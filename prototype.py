from sys import argv
from typing import Any

from textwrap import indent, dedent
import xml.etree.cElementTree as ET
from urllib.parse import urlparse

from requests import Session
from celadon import Application, Page, widgets, Widget, load_rules

WIDGET_TYPES = {
    key.lower(): value
    for key, value in vars(widgets).items()
    if isinstance(value, type) and issubclass(value, Widget)
}

STYLE_TEMPLATE = """\
{query}:
{indented_content}"""


def parse_rules(text: str, query: str | None = None) -> dict[str, Any]:
    if query is None:
        style = dedent(text)
    else:
        style = STYLE_TEMPLATE.format(
            query=query, indented_content=indent(dedent(text), 4 * " ")
        )

    return load_rules(style)


def parse_widget(node) -> tuple[Widget, dict[str, Any]]:
    cls = WIDGET_TYPES[node.tag]

    if "groups" in node.attrib:
        node.attrib["groups"] = node.attrib["groups"].split(" ")

    if node.text is not None and node.text.strip() != "":
        widget = cls(node.text.strip(), **node.attrib)
    else:
        widget = cls(**node.attrib)

    query = widget.as_query()
    rules = {}

    for child in node:
        if child.tag == "style":
            rules.update(**parse_rules(child.text, query))
            continue

        parsed, parsed_rules = parse_widget(child)

        widget += parsed
        rules.update(**parsed_rules)

    return widget, rules


def parse_page(text: str) -> Page:
    root = ET.fromstring(text)

    for first in root:
        page = Page(**first.attrib)

        for second in first:
            if second.tag in WIDGET_TYPES:
                widget, rules = parse_widget(second)
                page += widget

                for selector, rule in rules.items():
                    page.rule(selector, **rule)

            elif second.tag == "style":
                for selector, rule in parse_rules(second.text).items():
                    page.rule(selector, **rule)

            else:
                raise ValueError(second.tag)

    return page


class HttpApplication(Application):
    def __init__(self, domain: str, **app_args: Any) -> None:
        super().__init__(**app_args)

        self._url = urlparse(domain)
        self._session = Session()

    def route(self, destination: str) -> None:
        if destination.startswith("/"):
            destination = self._url.scheme + "://" + self._url.netloc + destination

        url = urlparse(destination)

        if url.netloc != self._url.netloc:
            self._url = url

        resp = self._session.get(destination)

        if not 200 <= resp.status_code < 300:
            self.stop()
            resp.raise_for_status()

        page = parse_page(resp.text)
        page.route_name = url.path

        # TODO: We don't have to request the page every time we go to it
        self.append(page)
        self._page = page

        if page.route_name == "/":
            self._terminal.set_title(self.title)

        else:
            self._terminal.set_title(page.title)

        self.apply_rules()


def main() -> None:
    if len(argv) < 2:
        print("please provide a url to load.")
        return

    url = argv[1]

    with HttpApplication(url, title="celx") as app:
        ...


if __name__ == "__main__":
    main()
