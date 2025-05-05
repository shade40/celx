from functools import wraps
from pathlib import Path
from threading import Thread
from time import time
from typing import Any, Callable
from urllib.parse import urlparse

from lxml.etree import fromstring as ElementTree, Element
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

from celadon import Application, Page, Widget, Container, Tower, Row, Text, Field, Button
from zenith import zml_escape
from requests import Session

from .parsing import parse_widget, parse_page
from .callbacks import (
    HTTPMethod,
    Instruction,
    Verb,
    TreeMethod,
)
from .lua import lua, init_runtime


__all__ = ["Browser"]


def threaded(func: Callable[..., None]) -> Callable[..., None]:
    """Returns a callable that runs the given function in a thread."""

    @wraps(func)
    def _inner(*args, **kwargs) -> None:
        Thread(target=func, args=args, kwargs=kwargs).start()

    return _inner


class Browser(Application):
    """An application class for HTTP pages."""

    def __init__(self, domain: str, **app_args: Any) -> None:
        super().__init__(**app_args)

        init_runtime(lua, self)

        self._registered_components = {}
        self._page = Page()
        self._url = urlparse(domain)
        self.url = self._url.geturl()
        self.history = []
        self.history_offset = 0
        self._session = Session()
        self._session.headers = {
            "Accepts": "text/celx",
            "CELX_Request": "true",
        }

        self._current_instructions: list[list[Instruction]] = []


        self.content = Tower(
            self._build_chrome(),
            Tower(eid="root"),
        )

        def _clear_instructions(_: Page) -> bool:
            for instructions in self._current_instructions:
                instructions.clear()

            return True

        self.on_page_changed += _clear_instructions

        self.route(self._url.geturl())

    def _build_chrome(self) -> Widget:
        with open(Path(__file__).parents[0] / "default_chrome.xml", "r") as f:
            xml = ElementTree(f.read())
            default_chrome, scripts = parse_page(xml, self._registered_components, self)

            for script in scripts:
                lua.execute(script)

        user_chrome = None
        user_chrome_path = (Path.home() / ".config" / "celx" / "chrome.xml")

        if user_chrome_path.exists():
            with open(user_chrome_path, "r") as f:
                xml = ElementTree(f.read())

                if "disabled" not in xml.attrib:
                    user_chrome, scripts = parse_page(xml, self._registered_components, self)

                    for script in scripts:
                        lua.execute(script)

        return user_chrome or default_chrome


    @property
    def session(self) -> Session:
        """Returns the current requests session."""

        return self._session

    def __getitem__(self, item: Any) -> Any:
        """Implement `__getitem__` for Lua attribute access."""

        return getattr(self, item)

    def _error(self, error: Exception) -> None:
        self.stop()

        self._raised = error

    def _prefix_endpoint(self, endpoint: str) -> str:
        """Prefixes hierarchy-only endpoints with the current url and its scheme."""

        if endpoint.startswith("/"):
            return self._url.scheme + "://" + self._url.netloc + endpoint

        return endpoint

    def _http(
        self,
        method: HTTPMethod,
        endpoint: str,
        data: dict[str, Any],
        handler: Callable[[Element], None],
    ) -> Thread:
        endpoint = self._prefix_endpoint(endpoint)

        if method is HTTPMethod.GET:
            request_data = {"params": data}
        else:
            request_data = {"data": data}

        if not isinstance(method, HTTPMethod):
            self._error(TypeError(f"Invalid method {method!r}."))

        request = getattr(self._session, method.value.lower())

        def _execute() -> None:
            resp = request(endpoint, **request_data)

            if not 200 <= resp.status_code < 300:
                self.stop()
                resp.raise_for_status()

            self._url = urlparse(endpoint)
            self.url = self._url.geturl()

            # Wrap invalid XML as text
            # TODO: Treat response differently based on Content-Type
            xml = resp.text

            try:
                _ = parseString(xml)
            except ExpatError:
                xml = zml_escape(xml)
                xml = f"<text>{xml}</text>"

            tree = ElementTree(xml)

            for sourceable in ["style", "script", "complib"]:
                for node in tree.findall(f".//{sourceable}[@src]"):
                    resp = self._session.get(self._prefix_endpoint(node.attrib["src"]))

                    if not 200 <= resp.status_code < 300:
                        self.stop()
                        resp.raise_for_status()

                    if sourceable == "complib":
                        sourced = ElementTree(resp.text)
                        for child in sourced:
                            node.append(child)

                        for key, value in sourced.attrib.items():
                            node.attrib[key] = value

                    else:
                        node.text = resp.text

                    del node.attrib["src"]

            return handler(tree)

        thread = Thread(target=_execute)
        thread.start()

        return thread

    def _xml_page_route(self, node: Element) -> None:
        """Routes to a page loaded from the given XML."""

        try:
            page_node = node.find("page")

            if page_node is None:
                raise ValueError("no <page /> node found.")

            page = Page(**page_node.attrib)

            widget, scripts = parse_page(page_node, self._registered_components, page)

            for script in scripts:
                lua.execute(script)

            self.content = Tower(
                self._build_chrome(),
                Tower(widget, eid="root"),
            )

            page.append(self.content)

        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._error(exc)
            return

        page.route_name = self._url.geturl()

        # TODO: We don't have to request the page every time we go to it
        self.append(page)

        self._page = page
        self._mouse_target = self._page[0]
        self.on_page_changed(page)

        if page.route_name == "/":
            self._terminal.set_title(self.title)

        else:
            self._terminal.set_title(page.title)

        self.apply_rules()
        self.page._rules_changed = True

    @threaded
    def run_instructions(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        self, instructions: list[Instruction], caller: Widget
    ) -> None:
        """Runs through a list of instructions."""

        result = None

        def _set_result(xml: Element) -> None:
            nonlocal result

            # Drill down to find the first widget, pass that on instead.
            if xml.tag == "celx":
                for node in xml.findall("./page//"):
                    if node.tag not in ["style", "script"]:
                        xml = node
                        break

                else:
                    self._error(ValueError("no widget in response"))
                    return

            result, rules = parse_widget(xml, self._registered_components)

            if self.page is None:
                return

            # TODO: There might be cases where we don't want to apply styles immediately,
            #       like when a future "DELETE" instruction is added.
            for selector, rule in rules.items():
                self.page.rule(selector, **rule)

            with open("log", "a") as f:
                f.write(str(rules) + "\n")

        self._current_instructions.append(instructions)

        try:  # pylint: disable=too-many-nested-blocks
            for instr in instructions:
                if instr.verb.value in HTTPMethod.__members__:
                    endpoint, container = instr.args
                    assert endpoint is not None

                    body: Widget | Page | None = caller.parent

                    if container is not None:
                        body = self.find(container)

                        if body is None:
                            raise ValueError(f"nothing matched selector {container!r}")

                    if not isinstance(body, Widget):
                        raise ValueError(f"request body {body!r} is not serializable")

                    content = body.serialize()

                    self._http(
                        HTTPMethod(instr.verb.value), endpoint, content, _set_result
                    ).join()

                    continue

                if instr.verb.value in TreeMethod.__members__:
                    if result is None:
                        raise ValueError("no result to update tree with")

                    selector, modifier = instr.args
                    assert selector is not None

                    target = self.find(selector)

                    if target is None:
                        raise ValueError(f"nothing matched selector {selector!r}")

                    if not isinstance(target, Container):
                        raise ValueError(
                            f"cannot modify tree of non-container {target!r}"
                        )

                    if instr.verb is Verb.SWAP:
                        offsets = {"before": -1, None: 0, "after": 1}

                        if modifier == "IN":
                            target.update_children([result])

                        elif modifier in offsets:
                            if not isinstance(target.parent, Container):
                                raise ValueError(
                                    "cannot modify tree of non-container parent of"
                                    + repr(target)
                                )

                            target.parent.replace(
                                target, result, offset=offsets[modifier]
                            )

                        else:
                            raise ValueError(
                                f"unknown modifier {modifier!r} for verb {instr.verb!r}"
                            )

                    elif instr.verb is Verb.INSERT:
                        if modifier == "IN":
                            target.insert(0, result)

                        else:
                            if not isinstance(target.parent, Container):
                                raise ValueError(
                                    "cannot modify tree of non-container parent of"
                                    + repr(target)
                                )

                            index = target.parent.children.index(target)
                            offsets = {"before": index, "after": index + 1}

                            if modifier not in offsets:
                                raise ValueError(
                                    f"unknown modifier {modifier!r}"
                                    + f" for verb {instr.verb!r}"
                                )

                            target.parent.insert(offsets[modifier], result)

                    elif instr.verb is Verb.APPEND:
                        if modifier != "IN":
                            raise ValueError(
                                f"unknown modifier {modifier!r} for verb {instr.verb!r}"
                            )

                        target.append(result)

                    # TODO: This is hacky as hell, but we need it for widgets to load in
                    #       .styles
                    parent = result.parent
                    self._init_widget(result)
                    result.parent = parent

                    continue

                if instr.verb is Verb.SELECT:
                    if result is None:
                        raise ValueError("no result to select from")

                    if not isinstance(result, Container):
                        raise ValueError(
                            f"cannot select from non container ({result!r})"
                        )

                    assert instr.args[0] is not None

                    result = self.find(instr.args[0], scope=result)
                    continue

        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._error(exc)
            return

        self._current_instructions.remove(instructions)

    def route(self, destination: str, no_history: bool = False) -> None:
        """Routes to the given URL."""

        if not no_history:
            self.history.append(destination)
            self.history_offset = 0

        destination = self._prefix_endpoint(destination)

        self._http(HTTPMethod.GET, destination, {}, self._xml_page_route)

    def refresh(self) -> None:
        """Reloads the current URL."""

        self._http(HTTPMethod.GET, self.url, {}, self._xml_page_route)

    def back(self) -> None:
        self.history_offset = min(self.history_offset + 1, len(self.history) - 1)
        self.route(self.history[-self.history_offset-1], no_history=True)

    def forward(self) -> None:
        self.history_offset = max(self.history_offset - 1, 0)
        self.route(self.history[-self.history_offset-1], no_history=True)
