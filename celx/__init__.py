"""A prototype celx browser.

Limitations (to be fixed after prototype):

- Blocking requests
- Little to no error handling
- Some _questionable_ code style (seriously, wtf is the nesting in `parse_callback`
"""

import re
from sys import argv
from typing import Any, Callable, Literal

from textwrap import indent, dedent
import xml.etree.cElementTree as ET
from urllib.parse import urlparse

from requests import Session, Response
from celadon import Application, Page, widgets, Widget, load_rules

WIDGET_TYPES = {
    key.lower(): value
    for key, value in vars(widgets).items()
    if isinstance(value, type) and issubclass(value, Widget)
}

STYLE_TEMPLATE = """\
{query}:
{indented_content}"""

__all__ = ["HttpApplication"]


def parse_rules(text: str, query: str | None = None) -> dict[str, Any]:
    """Parses a block of YAML rules into a dictionary."""

    if query is None:
        style = dedent(text)
    else:
        style = STYLE_TEMPLATE.format(
            query=query, indented_content=indent(dedent(text), 4 * " ")
        )

    return load_rules(style)


# There is massive repetition in this function, so we should fix that.
def parse_callback(value: str) -> Callable[[Widget], None]:
    """Parses a callback descriptor string into a callable.

    Current keywords & associated arguments:

    - GET(endpoint): Sends a GET request to `endpoint`, stores response text in `result`

    - POST(container?, endpoint): Serializes `container` and sends it as a POST request
        to endpoint, storing its response text in `result`.

    - swap(where?, target): Parses the XML in `result` as a widget, and replaces some
        part of `target` with it:

            where `where` in

            in => target.update_children
            before => target.parent.replace(target, offset=-1)
            after => target.parent.replace(target, offset=1)

    - insert|append(where?, target): Adds `result` without replacing.
    """

    lines = re.split("[;\n]", value)

    instructions = []

    for line in lines:
        ident, *args = line.strip().split(" ")

        if ident == "GET":
            instructions.append(("get", (args[0],)))

        elif ident == "POST":
            if len(args) == 2:
                container, endpoint = args
            else:
                container = None
                endpoint = args[0]

            instructions.append(("post", (endpoint, container)))

        elif ident == "swap":
            if len(args) == 2:
                where, target = args
            else:
                where = None
                target = args[0]

            instructions.append(("swap", (target, where)))

        elif ident == "insert":
            where, target = args

            instructions.append(("insert", (target, where)))

        elif ident == "append":
            where, target = args

            instructions.append(("append", (target, where)))

        else:
            raise ValueError(f"unknown ident {ident!r} in {line!r}")

    def _callback(self: Widget) -> bool:
        result = None
        app = self.app

        def _get(endpoint: str) -> str:
            return app.http_get(endpoint)

        def _post(endpoint: str, container: Widget | None = None) -> str:
            body = self.parent

            if container is not None:
                body = app.find(container)

            json = body.serialize()

            return app.http_post(endpoint, json)

        def _swap(
            target: str, where: Literal["in", "before", "after"] | None = None
        ) -> None:
            if result is None:
                raise ValueError("no result to swap with")

            target_widget = app.find(target)

            tree = ET.fromstring(result)
            widget = parse_widget(tree)[0]

            if where is None:
                target_widget.parent.replace(target_widget, widget)
                return

            if where == "in":
                target_widget.update_children([widget])
                return

            if where == "before":
                target_widget.parent.replace(target_widget, widget, offset=-1)
                return

            if where == "after":
                target_widget.parent.replace(target_widget, widget, offset=1)
                return

        def _insert(target: str, where: Literal["in", "before", "after"]) -> None:
            if result is None:
                raise ValueError("no result to swap with")

            target_widget = app.find(target)

            tree = ET.fromstring(result)
            widget = parse_widget(tree)[0]

            if where == "in":
                target_widget.insert(0, widget)
                return

            if where == "before":
                index = target_widget.parent.children.index(target_widget)
                target_widget.parent.insert(index, widget)
                return

            if where == "after":
                target_widget.parent.append(widget)
                return

        def _append(target: str, where: Literal["in", "before", "after"]) -> None:
            if result is None:
                raise ValueError("no result to swap with")

            target_widget = app.find(target)

            tree = ET.fromstring(result)
            widget = parse_widget(tree)[0]

            if where == "in":
                target_widget.append(0, widget)
                return

            if where == "before":
                index = target_widget.parent.children.index(target_widget)
                target_widget.parent.append(index, widget)
                return

            if where == "after":
                index = target_widget.parent.children.index(target_widget)
                target_widget.parent.insert(index, widget)
                return

        for instruction in instructions:
            func_name, args = instruction

            func = {
                "get": _get,
                "post": _post,
                "swap": _swap,
                "insert": _insert,
                "append": _append,
            }[func_name]

            result = func(*args)

        return True

    return _callback


def parse_widget(node) -> tuple[Widget, dict[str, Any]]:
    """Parses a widget out of an XML node.

    This also adjusts certain values given in the node's attributes:

    - groups: Replace `value` with `value.split(" ")`
    - on-*: Replace `value` with `parse_callback(value)`

    Returns:
        The resulting widget, as well as any styling the markup contained.
    """

    cls = WIDGET_TYPES[node.tag]

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

    if node.text is not None and node.text.strip() != "":
        widget = cls(node.text.strip(), **init)
    else:
        widget = cls(**init)

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
    """Parses a page out of the given text.

    This will also handle page-local style markup, but raises an error for any tag other
    than `page` and `style`.
    """

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
    """A Celadon application with HTTP capabilities."""

    def __init__(self, domain: str, **app_args: Any) -> None:
        super().__init__(**app_args)

        self._url = urlparse(domain)
        self._session = Session()
        self.route(self._url.geturl())

    @property
    def session(self) -> Session:
        return self._session

    def _handle_resp_errors(self, resp: Response) -> None:
        """Raises an error if the response isn't successful."""

        if not 200 <= resp.status_code < 300:
            self.stop()
            resp.raise_for_status()

    def _prefix_endpoint(self, endpoint: str) -> str:
        """Prefixes hierarchy-only endpoints with the current url and its scheme."""

        if endpoint.startswith("/"):
            return self._url.scheme + "://" + self._url.netloc + endpoint

        return endpoint

    def http_get(self, endpoint: str) -> str | None:
        """Gets the given endpoint, returns the response's text."""

        endpoint = self._prefix_endpoint(endpoint)

        resp = self._session.get(endpoint)
        self._handle_resp_errors(resp)

        return resp.text

    def http_post(self, endpoint: str, body: dict[str, str]) -> str | None:
        """Posts `body` to the given endpoint, returns the response's text."""

        endpoint = self._prefix_endpoint(endpoint)

        resp = self._session.post(endpoint, json=body)
        self._handle_resp_errors(resp)

        return resp.text

    def route(self, destination: str) -> None:
        """Routes to the given URL."""

        destination = self._prefix_endpoint(destination)

        xml = self.http_get(destination)
        url = urlparse(destination)

        if url.netloc != self._url.netloc:
            self._url = url

        page = parse_page(xml)
        page.route_name = url.path

        # TODO: We don't have to request the page every time we go to it
        self.append(page)
        self._page = page
        self._mouse_target = self._page[0]

        if page.route_name == "/":
            self._terminal.set_title(self.title)

        else:
            self._terminal.set_title(page.title)

        self.apply_rules()
