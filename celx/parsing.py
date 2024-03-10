import re
from xml.etree.ElementTree import Element

from typing import Any, Callable
from textwrap import indent, dedent

from celadon import Widget, load_rules, Page

from .lua import lua, WIDGET_TYPES
from .callbacks import parse_callback

STYLE_TEMPLATE = """\
{query}:
{indented_content}\
"""

LUA_SCRIPT_TEMPLATE = """\
function(widget)
    local env = {{}}

    for k, v in pairs(sandbox) do
        env[k] = v
    end

    local _ENV = env

    self = widget
    styles = styles(widget)

{indented_content}

    return _ENV
end\
"""


def lua_formatted_get_content(scope: dict[str, Any]) -> Callable[[Widget], list[str]]:
    """Returns a `get_content` method that formats Lua variables.

    You can use any variable available in the current scope using a $ prefix, like
    `$count`.
    """

    def _resolve(word: str, scope: dict[str, Any]) -> str:
        if "." not in word:
            return str(scope[word])

        *scopeids, word = word.split(".")

        inner = scope

        for scopeid in scopeids:
            if scopeid not in inner:
                raise ValueError(f"unregistered scopeid {scopeid!r}")

            inner = inner[scopeid]

        return str(inner[word])

    def _get_content(self: Widget) -> list[str]:
        lines = []

        for line in self.__class__.get_content(self):
            in_var = False
            parts = []

            for word in re.split(r"([^a-zA-Z0-9_\.])", line):
                if word == "$":
                    in_var = True
                    continue

                if in_var:
                    in_var = False

                    word = _resolve(word, scope)

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


def _looser_callback_wrapper(
    callback: Callable[[Widget | None], bool | None]
) -> Callable[[Widget], bool]:
    """Let's Lua create callbacks without arguments or return values.

    This is done becaues the Lua scope can usually already access the caller widget
    using the `self` variable.
    """

    def _wrapper(data: Widget) -> bool:
        try:
            res = callback(data)
        except TypeError:
            res = callback(data)

        if res is not None:
            return res

        # Assume handled if not otherwise stated
        return True

    return _wrapper


# TODO: Technically rules is more like a `dict[str, dict[str, <something>]]`!
def parse_widget(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    node: Element,
) -> tuple[Widget, dict[str, Any]]:
    """Parses a widget, its callbacks & its styling from an XML node."""

    init: dict[str, str | tuple[str, ...] | list[Callable[[Widget], bool]]] = {}

    for key, value in node.attrib.items():
        if key == "groups":
            init["groups"] = tuple(value.split(" "))
            continue

        if key.startswith("on-"):
            key = key.replace("-", "_")
            init[key] = [parse_callback(value)]
            continue

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
        widget = cls(text.strip(), **init)  # type: ignore
    else:
        widget = cls(**init)  # type: ignore

    query = widget.as_query()
    scope = None

    if (script_node := node.find("script")) is not None:
        # Set up widget & styles globals
        code = LUA_SCRIPT_TEMPLATE.format(
            indented_content=indent(dedent(script_node.text or ""), 4 * " ")
        )

        try:
            setup_scope = lua.eval(code)

        except Exception as err:
            raise ValueError(code) from err

        scope = setup_scope(widget)

        lua.eval("function(widget, scope) sandbox.scopes[widget] = scope end")(
            widget, scope
        )

        for key, value in scope.items():
            if key.startswith(("pre_", "on_")):
                event = getattr(widget, key)

                if event is None:
                    raise ValueError(f"invalid event handler {key!r}")

                assert callable(value)

                event += _looser_callback_wrapper(value)

        node.remove(script_node)

    rules: dict[str, Any] = {}

    # Save current outer scope
    old_outer = lua.eval("sandbox.outer")
    scope = scope or lua.table_from({"outer": lua.eval("sandbox.outer")})

    # Set outer scope to this widget's inner scope
    lua.eval("function(widget) sandbox.outer = sandbox.scopes[widget] end")(widget)

    for child in node:
        if child.tag == "style":
            rules.update(**parse_rules(child.text or "", query))
            continue

        parsed, parsed_rules = parse_widget(child)

        # This will error at runtime
        widget += parsed  # type: ignore

        rules.update(**parsed_rules)

    # Set formatted get content for the widget
    get_content = lua_formatted_get_content(scope)
    # We're overwriting the `get_content` method intentionally.
    widget.get_content = get_content.__get__(widget, widget.__class__)  # type: ignore

    # Reset outer scope to what it used to be
    lua.eval("function(scope) sandbox.outer = scope end")(old_outer)

    return widget, rules


def parse_page(node: Element) -> Page:
    """Parses a page, its scripts & its children from XML node."""

    page_node = node.find("page")

    if page_node is None:
        raise ValueError("no <page /> node found.")

    # Init args aren't strongly typed
    page = Page(**page_node.attrib)  # type: ignore

    for child in page_node:
        if child.tag in WIDGET_TYPES:
            widget, rules = parse_widget(child)
            page += widget

            for selector, rule in rules.items():
                page.rule(selector, **rule)

        elif child.tag == "style":
            for selector, rule in parse_rules(child.text or "").items():
                page.rule(selector, **rule)

        else:
            raise ValueError(child.tag)

    return page
