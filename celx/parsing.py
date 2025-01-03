import re
from lxml.etree import Element, tostring as element_to_string

import lupa
from copy import deepcopy
from typing import Any, Callable
from textwrap import indent, dedent

from celadon import Widget, load_rules, Page

from .lua import lua, LuaTable, WIDGET_TYPES
from .callbacks import parse_callback

STYLE_TEMPLATE = """\
{query}:
{indented_content}\
"""

LUA_SCRIPT_BEGIN_OUTER = """\
do table.insert(sandbox.stack, _ENV)
    scope = {{}}
    for k, v in pairs(sandbox) do
        scope[k] = v
    end

    _ENV = sandbox.initScope(scope)
    env_id = {script_id}

"""

LUA_SCRIPT_BEGIN_INNER = """\
do table.insert(stack, _ENV)
    _ENV = initScope(_ENV)
    env_id = {script_id}

"""

LUA_SCRIPT_END = """
envs[{script_id}] = _ENV
end _ENV = table.remove(stack)
if _children then table.insert(_children, envs[{script_id}]) end

"""

EVENT_PREFIXES = ("on", "pre")

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

    code = indent(
        (LUA_SCRIPT_BEGIN_OUTER if outer else LUA_SCRIPT_BEGIN_INNER).format(
            script_id=node_to_id[node]
        ),
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
            script.text = ""

            node.append(script)

        for key, value in params.items():
            script.text = script.text.replace(
                f"${key}", node.get(key, default=value)
            )

        slot = replacement.find("_slot")

        if slot is not None:
            slot_idx = [*replacement].index(slot)
            replacement.remove(slot)

            content = [*node]

            for i, child in enumerate(content):
                replacement[max(slot_idx - 1 + i, 0)].addnext(child)

        parent = node.getparent()
        idx = [*parent].index(node)

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

        parsed, parsed_rules = parse_widget(child, components, parse_script=False, result=result)
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

                event += value

        # Set formatted get content for the widget
        get_content = lua_formatted_get_content(env)
        widget.get_content = get_content.__get__(widget, widget.__class__)  # type: ignore

    return widget, rules

def _register_component(node: Element, components: dict[str, str], namespace: str | None = None) -> None:
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

def parse_page(node: Element, components: dict[str, str]) -> Page:
    """Parses a page, its scripts & its children from XML node."""

    page_node = node.find("page")

    if page_node is None:
        raise ValueError("no <page /> node found.")

    # Init args aren't strongly typed
    page = Page(**page_node.attrib)  # type: ignore

    for child in page_node:
        if child.tag == "complib":
            namespace = child.get("namespace")

            for inner in child:
                _register_component(inner, components, namespace)

            continue

        if child.tag == "component":
            _register_component(child, components)
            continue

        if child.tag in WIDGET_TYPES or child.tag in components:
            widget, rules = parse_widget(child, components)
            page += widget

            for selector, rule in rules.items():
                page.rule(selector, **rule)

        elif child.tag == "style":
            for selector, rule in parse_rules(child.text or "").items():
                page.rule(selector, **rule)

        else:
            raise ValueError(child.tag)

    return page
