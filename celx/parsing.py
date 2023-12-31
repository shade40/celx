import re
from xml.etree.ElementTree import Element

from dataclasses import dataclass
from enum import Enum
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
    def _get_content(self) -> None:
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

                    if "." in word:
                        *scopeids, word = word.split(".")

                        inner = scope

                        for scopeid in scopeids:
                            if scopeid not in inner:
                                raise ValueError(f"unregistered scopeid {scopeid!r}")

                            inner = inner[scopeid]

                        parts.append(str(inner[word]))
                        continue

                    word = str(scope[word])

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


def parse_widget(node: Element) -> Widget:
    init = {}

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
        widget = cls(text.strip(), **init)
    else:
        widget = cls(**init)

    query = widget.as_query()
    scope = None

    if (script_node := node.find("script")) is not None:
        # Set up widget & styles globals
        code = LUA_SCRIPT_TEMPLATE.format(
            indented_content=indent(dedent(script_node.text), 4 * " ")
        )

        try:
            setup_scope = lua.eval(code)

        except Exception as err:
            raise ValueError(code)

        scope = setup_scope(widget)

        lua.eval("function(widget, scope) sandbox.scopes[widget] = scope end")(
            widget, scope
        )

        for key, value in scope.items():
            if key.startswith(("pre_", "on_")):
                event = getattr(widget, key)

                if event is None:
                    raise ValueError(f"invalid event handler {key!r}")

                event += value

        node.remove(script_node)

    rules = {}

    # Save current outer scope
    old_outer = lua.eval("sandbox.outer")
    scope = scope or lua.table_from({"outer": lua.eval("sandbox.outer")})

    # Set outer scope to this widget's inner scope
    lua.eval("function(widget) sandbox.outer = sandbox.scopes[widget] end")(widget)

    for child in node:
        if child.tag == "style":
            rules.update(**parse_rules(child.text, query))
            continue

        parsed, parsed_rules = parse_widget(child)

        widget += parsed
        rules.update(**parsed_rules)

    # Set formatted get content for the widget
    get_content = lua_formatted_get_content(scope)
    widget.get_content = get_content.__get__(widget, widget.__class__)

    # Reset outer scope to what it used to be
    lua.eval("function(scope) sandbox.outer = scope end")(old_outer)

    return widget, rules


def parse_page(node: Element) -> Page:
    page_node = node.find("page")

    page = Page(**page_node.attrib)

    for child in page_node:
        if child.tag in WIDGET_TYPES:
            widget, rules = parse_widget(child)
            page += widget

            for selector, rule in rules.items():
                page.rule(selector, **rule)

        elif child.tag == "style":
            for selector, rule in parse_rules(child.text).items():
                page.rule(selector, **rule)

        else:
            raise ValueError(child.tag)

    return page
