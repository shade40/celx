from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Type

from lupa import LuaRuntime  # type: ignore # pylint: disable=no-name-in-module
from celadon import Widget, widgets
from zenith import zml_alias, zml_macro, MacroType

from .callbacks import parse_callback

if TYPE_CHECKING:
    from .application import HttpApplication

WIDGET_TYPES = {
    key.lower(): value
    for key, value in vars(widgets).items()
    if isinstance(value, type) and issubclass(value, Widget)
}


def _attr_filter(_, attr, __):
    """Removes access to sunder and dunder attributes in Lua code."""

    if not isinstance(attr, str):
        return attr

    if attr.startswith("_"):
        raise AttributeError("access denied")

    return attr


class LuaStyleWrapper:
    """Wraps a widget's style object for nice Lua syntax.

    ```
    styles.content = 'red'
    styles(some_widget).content = 'blue'
    ```
    """

    def __init__(self, widget: Widget) -> None:
        self._widget = widget

    def __setattr__(self, attr: str, value: Any) -> None:
        if attr == "_widget":
            super().__setattr__(attr, value)

            return

        self._widget.app.rule(
            self._widget.as_query(), score=9999, **{f"{attr}_style": value}
        )

    def __call__(self, widget: Widget) -> LuaStyleWrapper:
        return self.__class__(widget)


def _multi_find(
    app: "HttpApplication", selector: str, multiple: bool = False
) -> Widget | list[Widget] | None:
    """Finds widgets from the application."""

    if multiple:
        return lua.table_from([*app.find_all(selector)])

    return app.find(selector)


def _zml_define(name: str, macro: MacroType) -> None:
    """Defines a macro in Lua."""

    def _inner(*args) -> str:
        return macro(*args)

    _inner.__name__ = name.replace(" ", "_")
    zml_macro(_inner)


def _chocl(descriptor: str) -> Callable[[Widget], bool]:
    """Provides Lua access to the celx hypermedia-oriented callback language."""

    return parse_callback(descriptor)


def _remove_and_callback_with(
    dialogue: widgets.Dialogue, callback: Callable, value: Any
) -> bool:
    dialogue.remove_from_parent()
    callback(value)

    return False


def _confirm(
    app: "HttpApplication", title: str, body: str, callback: Callable[[bool], None]
) -> None:
    """Adds a confirmation dialogue."""

    dialogue: widgets.Dialogue

    dialogue = widgets.Dialogue(
        widgets.Text(title, group="title"),
        widgets.Text(body, group="body"),
        widgets.Row(
            widgets.Button(
                "Confirm",
                on_submit=[
                    lambda _: _remove_and_callback_with(dialogue, callback, True)
                ],
            ),
            widgets.Button(
                "Deny",
                on_submit=[
                    lambda _: _remove_and_callback_with(dialogue, callback, False)
                ],
            ),
            group="input",
        ),
    )
    app.pin(dialogue)


def _alert(app: "HttpApplication", text: str) -> None:
    """Adds an alert dialogue."""

    dialogue: widgets.Dialogue

    def _remove(_: Widget) -> bool:
        dialogue.remove_from_parent()

        return True

    dialogue = widgets.Dialogue(
        widgets.Text(text, group="body"),
        widgets.Row(
            widgets.Button(
                "Close",
                on_submit=[_remove],
            ),
            group="input",
        ),
    )

    app.pin(dialogue)


def _prompt(
    app: "HttpApplication",
    title: str,
    body: dict[int, Widget],
    callback: Callable[[Widget], bool],
) -> None:
    """Adds a prompt dialogue with custom widgets."""

    dialogue = widgets.Dialogue(
        widgets.Text(title, group="title"),
        widgets.Tower(*body.values(), group="body"),
        widgets.Row(
            widgets.Button(
                "Submit",
                on_submit=[
                    lambda self: _remove_and_callback_with(
                        dialogue, callback, self.parent
                    )
                ],
            ),
            group="input",
        ),
    )

    app.pin(dialogue)


# TODO: This takes a lua table, not "Any"!
def _widget_factory(typ: Type[Widget]) -> Callable[[Any], Widget]:
    """Lets Lua instantiate widgets.

    ```
    Button{"label", on_submit={function() alert("hey") end }}
    ```
    """

    def _create(options) -> Widget:
        args = []
        kwargs = {}

        for key, value in options.items():
            if isinstance(key, int):
                args.append(value)
                continue

            if key == "groups":
                value = tuple(value.values())

            # Likely a Lua table
            elif hasattr(value, "values"):
                if all(isinstance(val, int) for val in list(value)):
                    value = [*value.values()]
                else:
                    value = dict(value.items())

            kwargs[key] = value

        return typ(*args, **kwargs)

    return _create


def init_runtime(runtime: LuaRuntime, app: "HttpApplication") -> None:
    """Sets up the global namespace for the given runtime."""

    runtime.execute(
        """
        sandbox = {
          ipairs = ipairs,
          next = next,
          pairs = pairs,
          pcall = pcall,
          tonumber = tonumber,
          tostring = tostring,
          type = type,
          unpack = unpack,
          coroutine = { create = coroutine.create, resume = coroutine.resume,
              running = coroutine.running, status = coroutine.status,
              wrap = coroutine.wrap },
          string = { byte = string.byte, char = string.char, find = string.find,
              format = string.format, gmatch = string.gmatch, gsub = string.gsub,
              len = string.len, lower = string.lower, match = string.match,
              rep = string.rep, reverse = string.reverse, sub = string.sub,
              upper = string.upper },
          table = { insert = table.insert, maxn = table.maxn, remove = table.remove,
              sort = table.sort },
          math = { abs = math.abs, acos = math.acos, asin = math.asin,
              atan = math.atan, atan2 = math.atan2, ceil = math.ceil, cos = math.cos,
              cosh = math.cosh, deg = math.deg, exp = math.exp, floor = math.floor,
              fmod = math.fmod, frexp = math.frexp, huge = math.huge,
              ldexp = math.ldexp, log = math.log, log10 = math.log10, max = math.max,
              min = math.min, modf = math.modf, pi = math.pi, pow = math.pow,
              rad = math.rad, random = math.random, sin = math.sin, sinh = math.sinh,
              sqrt = math.sqrt, tan = math.tan, tanh = math.tanh },
          os = { clock = os.clock, difftime = os.difftime, time = os.time },
          scopes = {},
        }
        """
    )

    inject = lua.eval("function(obj, name) sandbox[name] = obj end")

    inject({"alias": zml_alias, "define": _zml_define}, "zml")
    inject(app.timeout, "timeout")
    inject(_chocl, "chocl")

    inject(partial(_alert, app), "alert")
    inject(partial(_confirm, app), "confirm")
    inject(partial(_prompt, app), "prompt")
    inject(partial(_multi_find, app), "find")

    inject(LuaStyleWrapper, "styles")
    inject(
        {key.title(): _widget_factory(value) for key, value in WIDGET_TYPES.items()},
        "w",
    )


lua = LuaRuntime(
    register_eval=False,
    register_builtins=False,
    attribute_filter=_attr_filter,
)
