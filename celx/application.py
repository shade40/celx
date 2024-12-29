from functools import wraps
from typing import Any, Callable
from threading import Thread
from urllib.parse import urlparse

from xml.etree.ElementTree import fromstring as ElementTree, Element

from celadon import Application, Page, Widget, Container
from requests import Session

from .parsing import parse_widget, parse_page
from .callbacks import (
    HTTPMethod,
    Instruction,
    Verb,
    TreeMethod,
)
from .lua import lua, init_runtime


__all__ = ["HttpApplication"]


def threaded(func: Callable[..., None]) -> Callable[..., None]:
    """Returns a callable that runs the given function in a thread."""

    @wraps(func)
    def _inner(*args, **kwargs) -> None:
        Thread(target=func, args=args, kwargs=kwargs).start()

    return _inner


class HttpApplication(Application):
    """An application class for HTTP pages."""

    def __init__(self, domain: str, **app_args: Any) -> None:
        super().__init__(**app_args)

        init_runtime(lua, self)

        self._page = Page()
        self._url = urlparse(domain)
        self._session = Session()
        self._session.headers = {
            "Accepts": "text/celx",
            "CELX_Request": "true",
        }
        self._current_instructions: list[list[Instruction]] = []

        def _clear_instructions(_: Page) -> bool:
            for instructions in self._current_instructions:
                instructions.clear()

            return True

        self.on_page_changed += _clear_instructions

        self.route(self._url.geturl())

    @property
    def session(self) -> Session:
        """Returns the current requests session."""

        return self._session

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
            request_data = {"json": data}

        if not isinstance(method, HTTPMethod):
            self._error(TypeError(f"Invalid method {method!r}."))

        request = getattr(self._session, method.value.lower())

        def _execute() -> None:
            resp = request(endpoint, **request_data)

            if not 200 <= resp.status_code < 300:
                self.stop()
                resp.raise_for_status()

            url = urlparse(endpoint)

            if url.netloc != self._url.netloc:
                self._url = url

            tree = ElementTree(resp.text)

            for sourceable in ["style", "script"]:
                for node in tree.findall(f".//{sourceable}[@src]"):
                    resp = self._session.get(self._prefix_endpoint(node.attrib["src"]))

                    if not 200 <= resp.status_code < 300:
                        self.stop()
                        resp.raise_for_status()

                    node.text = resp.text
                    del node.attrib["src"]

            return handler(tree)

        thread = Thread(target=_execute)
        thread.start()

        return thread

    def _xml_page_route(self, node: Element) -> None:
        """Routes to a page loaded from the given XML."""

        try:
            page = parse_page(node)

        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._error(exc)
            return

        page.route_name = self._url.path

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

            result, rules = parse_widget(xml)

            if self.page is None:
                return

            # TODO: There might be cases where we don't want to apply styles immediately,
            #       like when a future "DELETE" instruction is added.
            for selector, rule in rules.items():
                self.page.rule(selector, **rule)

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

                        if modifier == "in":
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
                        if modifier == "in":
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
                        if modifier != "in":
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

    def route(self, destination: str) -> None:
        """Routes to the given URL."""

        destination = self._prefix_endpoint(destination)

        self._http(HTTPMethod.GET, destination, {}, self._xml_page_route)
