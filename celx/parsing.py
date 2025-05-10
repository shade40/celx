import re
from lxml.etree import Element, fromstring, tostring

import lupa
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable
from textwrap import indent, dedent

from celadon import Widget, load_rules, Page

from .lua import lua, LuaTable, WIDGET_TYPES
from .callbacks import parse_callback

STYLE_TEMPLATE = """\
{query}:
{indented_content}\
"""

LUA_SCRIPT_BEGIN = """\
do table.insert(stack, _ENV)
    _ENV = initScope(_ENV)
    env_id = {script_id}

    -- USER CODE BEGIN
"""

LUA_SCRIPT_END = """
    -- USER CODE END

envs[{script_id}] = _ENV
end _ENV = table.remove(stack)
if _children then table.insert(_children, envs[{script_id}]) end

"""

EVENT_PREFIXES = ("on", "pre")

RE_ERROR_LINENO = re.compile('\[string "<python>"\]:(\d+):')

@dataclass
class RuntimeError(Exception):
    funcname: str
    widget: Widget
    code: str
    exc: lupa.LuaError

    lineno: int = -1

    def __post_init__(self):
        if (match := RE_ERROR_LINENO.search(str(self.exc))) is None:
            return

        self.lineno = int(match[1]) - 1

    def __str__(self):
        dedented = dedent("\n".join(self.code.splitlines()[self.lineno - 4 : self.lineno + 5]))
        lines = indent(dedented, 2 * " ").splitlines()

        lines[4] = "> " + dedented.splitlines()[4]

        start = None
        end = None

        for i, line in enumerate(lines):
            if "-- USER CODE BEGIN" in line:
                start = i
                continue

            if "-- USER CODE END" in line:
                end = i

        snippet = "\n".join(lines[start:end])

        return f"error in '{self.funcname}'\n\n{self.widget.as_query()}:\n\n" + dedent(snippet)

# TODO: This breaks `width: shrink` for text
def lua_formatted_get_content(scope: dict[str, Any]) -> Callable[[Widget], list[str]]:
    """Returns a `get_content` method that formats Lua variables.

    You can use any variable available in the current scope using a $ prefix, like
    `$count`.
    """

    def _get_content(self: Widget) -> list[str]:
        lines = []

        for line in self.__class__.get_content(self):
            in_var = False
            parts = []
            word = ""

            for word in re.split(r"([^a-zA-Z0-9_\.])", line):
                if word == "$":
                    in_var = True
                    continue

                if in_var:
                    in_var = False

                    value = scope[word]

                    if value is None:
                        raise ValueError(
                            f"unknown variable '{word}' for {self.as_query()}"
                        )

                    word = str(value)

                parts.append(word)

            lines.append("".join(parts))

        return lines

    return _get_content


def parse_rules(text: str, query: str | None = None) -> dict[str, Any]:
    """Parses a block of YAML rules into a dictionary."""

    if query is None:
        style = dedent(text)
    else:
        style = STYLE_TEMPLATE.format(
            query=query, indented_content=indent(dedent(text), 4 * " ")
        )

    return load_rules(style)


def _extract_script(
    node: Element, node_to_id: dict[Element, int], outer: bool = False, level: int = 0
) -> str:
    """Recursively extracts scripts starting from the given node."""

    code = ""

    if outer:
        code += "_ENV = sandbox.envs[0]\n\n"

    code += indent(
        LUA_SCRIPT_BEGIN.format(script_id=node_to_id[node]),
        level * 4 * " ",
    )

    for child in node:
        if child.tag == "style":
            continue

        if child.tag == "script":
            code += indent(dedent(child.text), (level + 1) * 4 * " ")
            continue

        code += _extract_script(child, node_to_id, level=level + 1)

    code += indent(LUA_SCRIPT_END.format(script_id=node_to_id[node]), level * 4 * " ")

    return code


def _get_pairs(table: LuaTable) -> list[str]:
    """Iterates through the `__pairs` of a Lua table."""

    iterator, state, first_key = lua.globals().pairs(table)

    while True:
        item = iterator(state, first_key)

        if item is None:
            break

        key, value = item

        yield (key, value)
        first_key = key


# TODO: Technically rules is more like a `dict[str, dict[str, <something>]]`!
def parse_widget(
    node: Element,
    components: dict[str, tuple[dict[str, Any], str]],
    parse_script: bool = True,
    result: dict[str, list[Widget, Element]] | None = None,
) -> tuple[Widget, dict[str, Any]]:
    """Parses a widget, its scripts & its styling from an XML node."""

    result = result or {}

    init: dict[str, str | tuple[str, ...] | list[Callable[[Widget], bool]]] = {}

    if node.tag in components:
        params, replacement = components[node.tag]
        replacement = deepcopy(replacement)

        script = replacement.find("script")

        if script is None:
            script = Element("script")
            script.text = " "

            node.append(script)

        slot = replacement.find("_slot")

        if slot is not None:
            slot_idx = [*replacement].index(slot)
            replacement.remove(slot)

            content = [*node]

            for i, child in enumerate(content):
                replacement[max(slot_idx - 1 + i, 0)].addnext(child)

        parent = node.getparent()
        idx = [*parent].index(node)

        text = tostring(replacement).decode()

        for key, value in params.items():
            text = text.replace(f"${key}", node.get(key, default=value))

        replacement = fromstring(text.encode())

        node = replacement
        parent[idx] = replacement

    for key, value in node.attrib.items():
        if key == "groups":
            init["groups"] = tuple(value.split(" "))
            continue

        if key.startswith(EVENT_PREFIXES):
            key = key.replace("-", "_")

            if value.startswith(":"):
                init[key] = [parse_callback(value)]

            else:
                script_node = node.find("script")

                if script_node is None:
                    script_node = Element("script")
                    script_node.text = ""

                script_node.text += f"function {key}() {value} end\n\n"
                node.append(script_node)

            continue

        key = key.replace("-", "_")

        if value.isdigit():
            value = int(value)

        elif value.lstrip("-+").replace(".", "", 1).isdigit():
            value = float(value)

        init[key] = value

    text = node.text

    if text is None or text.strip() == "":
        text = ""
        skipped = 0
        total = 0

        for total, child in enumerate(node):
            if child.tail is None:
                skipped += 1
                continue

            text = text + child.tail

        if skipped == total + 1:
            text = None

    cls = WIDGET_TYPES[node.tag]

    if text is not None and text.strip() != "":
        # The init args aren't strongly typed.
        widget = cls(dedent(text).strip("\n"), **init)  # type: ignore
    else:
        widget = cls(**init)  # type: ignore

    query = widget.as_query()
    scope = None

    rules: dict[str, Any] = {}

    script_id = id(widget)
    result[script_id] = widget, node

    for child in node:
        if child.tag == "style":
            rules.update(**parse_rules(child.text or "", query))
            continue

        if child.tag == "script":
            continue

        parsed, parsed_rules = parse_widget(
            child, components, parse_script=False, result=result
        )
        rules.update(**parsed_rules)
        widget += parsed  # type: ignore

        if child.tag in WIDGET_TYPES:
            result[id(parsed)] = parsed, child

    if parse_script:
        code = _extract_script(
            node, {node: s_id for s_id, [_, node] in result.items()}, outer=True
        )

    if not parse_script:
        return widget, rules

    sandbox = lua.eval("sandbox")
    envs = lua.eval("sandbox.envs")
    setfenv = lua.eval("builtins.setfenv")

    try:
        lua.execute(code)
    except lupa.LuaSyntaxError as exc:
        # TODO: This could alert() instead and abort exec
        raise exc

    for s_id, [widget, _] in reversed(result.items()):
        env = envs[s_id]

        if env is None:
            continue

        env.self = widget

        for key, value in _get_pairs(env):
            if sandbox[key] is not None:
                continue

            if callable(value):
                if not env.hasOwn(key):
                    continue

                value = setfenv(value, env)

            if key == "init":
                value()
                continue

            if isinstance(key, str) and key.startswith(EVENT_PREFIXES):
                event = getattr(widget, key, None)

                if event is None:
                    raise ValueError(f"invalid event handler {key!r}")

                assert callable(value)

                event += _report_env_id(value, s_id, code, widget, key)

        # Set formatted get content for the widget
        get_content = lua_formatted_get_content(env)
        widget.get_content = get_content.__get__(widget, widget.__class__)  # type: ignore

    return widget, rules

def _report_env_id(callback, env_id, code, widget, key):
    """Wraps a function and reports its environment id with exceptions it raises."""

    def _inner(*args, **kwargs):
        try:
            return callback(*args, **kwargs)

        except Exception as e:
            raise RuntimeError(key, widget, code, e)

    return _inner


def _register_component(
    node: Element, components: dict[str, str], namespace: str | None = None
) -> None:
    name = None
    params = {}

    for key, value in node.attrib.items():
        if key == "name":
            name = value
            continue

        params[key] = value

    if name is None:
        raise ValueError("components must have a name.")

    if namespace is not None:
        name = namespace + "." + name

    components[name] = params, node[0]


def parse_page(page_node: Element, components: dict[str, str], page: Page) -> tuple[Widget | None, list[str]]:
    """Parses a page, its scripts & its children from XML node."""

    content_nodes = [node for node in page_node if node.tag not in ["component", "complib", "style", "script"]]

    if len(content_nodes) > 1:
        raise ValueError("pages must have exactly one content node.", content_nodes)

    root = None
    scripts = [];

    for child in page_node:
        if child.tag == "complib":
            namespace = child.get("namespace")

            for inner in child:
                _register_component(inner, components, namespace)

            continue

        if child.tag == "component":
            _register_component(child, components)
            continue

        if child.tag == "style":
            for selector, rule in parse_rules(child.text or "").items():
                page.rule(selector, **rule)

            continue

        if child.tag == "script":
            scripts.append("_ENV = sandbox.envs[0]\n" + dedent(child.text))
            continue

        if child.tag in WIDGET_TYPES or child.tag in components:
            root, rules = parse_widget(child, components)

            for selector, rule in rules.items():
                page.rule(selector, **rule)

        else:
            raise ValueError(child.tag)

    return root, scripts
