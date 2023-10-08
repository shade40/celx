import re
from xml.etree.ElementTree import Element

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable
from textwrap import indent, dedent

from celadon import Widget, widgets, load_rules, Page

WIDGET_TYPES = {
    key.lower(): value
    for key, value in vars(widgets).items()
    if isinstance(value, type) and issubclass(value, Widget)
}


STYLE_TEMPLATE = """\
{query}:
{indented_content}"""


class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
    PUT = "PUT"
    PATCH = "PATCH"


class TreeMethod(Enum):
    INSERT = "INSERT"
    SWAP = "SWAP"
    APPEND = "APPEND"


class Verb(Enum):
    GET = HTTPMethod.GET.value
    POST = HTTPMethod.POST.value
    DELETE = HTTPMethod.DELETE.value
    PUT = HTTPMethod.PUT.value
    PATCH = HTTPMethod.PATCH.value

    INSERT = TreeMethod.INSERT.value
    SWAP = TreeMethod.SWAP.value
    APPEND = TreeMethod.APPEND.value

    SELECT = "SELECT"


@dataclass
class Instruction:
    verb: Verb
    args: tuple[str, ...]


def _instruction_runner(instructions: list[Instruction]) -> Callable[[str], bool]:
    """Creates a function to runs the given instructions on the calller widget's app."""

    def _interpret(self: Widget) -> bool:
        self.app.run_instructions(instructions, self)

    return _interpret


def parse_callback(text: str) -> Callable[[str], bool]:
    """Parses a callback descriptor into a list of Instructions."""

    lines = re.split("[;\n]", text)

    instructions = []

    for line in lines:
        verb_str, *args = line.strip().split()
        verb = Verb(verb_str.upper())

        if verb is Verb.SELECT:
            if len(args) > 1:
                raise ValueError(f"too many arguments for verb {verb!r}")

            instructions.append(Instruction(verb, (args[0],)))

        else:
            if len(args) > 2:
                raise ValueError(f"too many arguments for verb {verb!r}")

            modifier = None
            arg = args[0]

            if len(args) == 2:
                modifier, arg = args

            instructions.append(Instruction(verb, (arg, modifier)))

    return _instruction_runner(instructions)


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

    if text is None:
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
    rules = {}

    for child in node:
        if child.tag == "styles":
            rules.update(**parse_rules(child.text, query))
            continue

        parsed, parsed_rules = parse_widget(child)

        widget += parsed
        rules.update(**parsed_rules)

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

        elif child.tag == "styles":
            for selector, rule in parse_rules(child.text).items():
                page.rule(selector, **rule)

        else:
            raise ValueError(child.tag)

    return page
