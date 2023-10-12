from functools import wraps
from typing import Any, Callable
from threading import Thread
from urllib.parse import urlparse

from xml.etree.ElementTree import fromstring as ElementTree, Element

from celadon import Application, Page, Widget, Container
from requests import Session, Response

from .parsing import HTTPMethod, Instruction, Verb, TreeMethod, parse_widget, parse_page
from .lua import lua, init_runtime


__all__ = ["HttpApplication"]


def threaded(func: Callable[..., None]) -> Callable[..., None]:
    @wraps(func)
    def _inner(*args, **kwargs) -> None:
        Thread(target=func, args=args, kwargs=kwargs).start()

    return _inner


class HttpApplication(Application):
    def __init__(self, domain: str, **app_args: Any) -> None:
        super().__init__(**app_args)

        init_runtime(lua, self)

        self._page = Page()
        self._url = urlparse(domain)
        self._session = Session()
        self._current_instructions = []

        def _clear_instructions():
            for instructions in self._current_instructions:
                instructions.clear()

        self.on_page_changed += _clear_instructions

        self.route(self._url.geturl())

    @property
    def session(self) -> Session:
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
        handler: Callable[[str], None],
    ) -> None:
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

            for sourceable in ["styles", "lua"]:
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
        except Exception as exc:
            self._error(exc)
            return

        page.route_name = self._url.path

        # TODO: We don't have to request the page every time we go to it
        self.append(page)

        self._page = page
        self._mouse_target = self._page[0]
        self.on_page_changed()

        if page.route_name == "/":
            self._terminal.set_title(self.title)

        else:
            self._terminal.set_title(page.title)

        self.apply_rules()

    @threaded
    def run_instructions(self, instructions: list[Instruction], caller: Widget) -> None:
        """Runs through a list of instructions."""

        result = None

        def _set_result(xml: ElementTree) -> None:
            nonlocal result

            # Drill down to find the first widget, pass that on instead.
            if xml.tag == "celx":
                for node in xml.findall("./page//"):
                    if node.tag not in ["styles", "lua"]:
                        xml = node
                        break

                else:
                    self._error(ValueError("no widget in response"))
                    return

            result = parse_widget(xml)[0]

        self._current_instructions.append(instructions)

        for instr in instructions:
            if instr.verb.value in HTTPMethod.__members__:
                endpoint, container = instr.args

                body = caller.parent

                if container is not None:
                    try:
                        body = self.find(container)
                    except Exception as exc:
                        self._error(exc)
                        return

                    if body is None:
                        self._error(
                            ValueError(f"nothing matched selector {container!r}")
                        )
                        return

                content = body.serialize()

                self._http(
                    HTTPMethod(instr.verb.value), endpoint, content, _set_result
                ).join()

                continue

            if instr.verb.value in TreeMethod.__members__:
                if result is None:
                    self._error(ValueError("no result to update tree with"))
                    return

                selector, modifier = instr.args

                try:
                    target = self.find(selector)
                except Exception as exc:
                    self._error(exc)

                if target is None:
                    self._error(ValueError(f"nothing matched selector {selector!r}"))
                    return

                if instr.verb is Verb.SWAP:
                    offsets = {"before": -1, None: 0, "after": 1}

                    if modifier == "in":
                        target.update_children([result])

                    elif modifier in offsets:
                        target.parent.replace(target, result, offset=offsets[modifier])

                    else:
                        self._error(
                            ValueError(
                                f"unknown modifier {modifier!r} for verb {instr.verb!r}"
                            )
                        )
                        return

                elif instr.verb is Verb.INSERT:
                    if modifier == "in":
                        target.insert(0, result)
                    else:
                        index = target.parent.children.index(target)
                        offsets = {"before": index, "after": index + 1}

                        if modifier not in offsets:
                            self._error(
                                ValueError(
                                    f"unknown modifier {modifier!r}"
                                    + f" for verb {instr.verb!r}"
                                )
                            )
                            return

                        target.parent.insert(offsets[modifier], result)

                elif instr.verb is Verb.APPEND:
                    if modifier != "in":
                        self._error(
                            ValueError(
                                f"unknown modifier {modifier!r} for verb {instr.verb!r}"
                            )
                        )
                        return

                    target.append(result)

                # TODO: This is hacky as hell, but we need it for widgets to load in
                #       .styles
                parent = result.parent
                self._init_widget(result)
                result.parent = parent

                continue

            if instr.verb is Verb.SELECT:
                if result is None:
                    self._error(ValueError("no result to select from"))
                    return

                if not isinstance(result, Container):
                    self._error(
                        ValueError(f"cannot select from non container ({result!r})")
                    )
                    return

                try:
                    result = self.find(instr.args[0], scope=result)
                except Exception as exc:
                    self._error(exc)
                    return

                continue

        self._current_instructions.remove(instructions)

    def route(self, destination: str) -> None:
        """Routes to the given URL."""

        destination = self._prefix_endpoint(destination)

        self._http(HTTPMethod.GET, destination, {}, self._xml_page_route)
