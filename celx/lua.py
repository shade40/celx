from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lupa import LuaRuntime
from celadon import Widget, widgets
from celadon.style_map import StyleMap
from zenith import zml_alias, zml_macro

from .callbacks import parse_callback

if TYPE_CHECKING:
    from .application import HttpApplication

WIDGET_TYPES = {
    key.lower(): value
    for key, value in vars(widgets).items()
    if isinstance(value, type) and issubclass(value, Widget)
}


def _attr_filter(obj, attr, is_setting):
    if attr.startswith("_"):
        raise AttributeError("access denied")

    return attr


class LuaStyleWrapper:
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


def init_runtime(runtime: LuaRuntime, application: "HttpApplication") -> None:
    def _multi_find(selector: str, multiple: bool = False) -> Widget | list[Widget]:
        if multiple:
            return lua.table_from([*application.find_all(selector)])

        return application.find(selector)

    def _zml_define(name: str, macro: MacroType) -> None:
        def _inner(*args) -> str:
            return macro(*args)

        _inner.__name__ = name.replace(" ", "_")
        zml_macro(_inner)

    def _chocl(descriptor: str) -> Callable[[Widget], None]:
        return parse_callback(descriptor)

    def _confirm(title: str, body: str, callback: Callable[[bool], None]) -> None:
        dialogue = widgets.Dialogue(
            widgets.Text(title, group="title"),
            widgets.Text(body, group="body"),
            widgets.Row(
                widgets.Button(
                    "Confirm",
                    on_submit=[
                        lambda self: (dialogue.remove_from_parent(), callback(True))
                        and False
                    ],
                ),
                widgets.Button(
                    "Deny",
                    on_submit=[
                        lambda self: (dialogue.remove_from_parent(), callback(False))
                        and False
                    ],
                ),
                group="input",
            ),
        )
        application.pin(dialogue)

    def _alert(text: str) -> None:
        dialogue = widgets.Dialogue(
            widgets.Text(text, group="body"),
            widgets.Row(
                widgets.Button(
                    "Close",
                    on_submit=[lambda: dialogue.remove_from_parent()],
                ),
                group="input",
            ),
        )

        application.pin(dialogue)

    def _prompt(
        title: str, body: dict[int, Widget], callback: Callable[[Widget], None]
    ) -> None:
        dialogue = widgets.Dialogue(
            widgets.Text(title, group="title"),
            widgets.Tower(*body.values(), group="body"),
            widgets.Row(
                widgets.Button(
                    "Submit",
                    on_submit=[
                        lambda self: (
                            dialogue.remove_from_parent(),
                            callback(self.parent),
                        )
                        and False
                    ],
                ),
                group="input",
            ),
        )

        application.pin(dialogue)

    def _widget_factory(typ: Type[Widget]) -> None:
        def _create(options) -> None:
            args = []
            kwargs = {}

            for key, value in options.items():
                if isinstance(key, int):
                    args.append(value)
                    continue

                kwargs[key] = value

            return typ(*args, **kwargs)

        return _create

    lua.execute(
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
    inject(_chocl, "chocl")
    inject(_alert, "alert")
    inject(_confirm, "confirm")
    inject(_prompt, "prompt")
    inject(application.timeout, "timeout")
    inject(
        {key.title(): _widget_factory(value) for key, value in WIDGET_TYPES.items()},
        "w",
    )
    inject(_multi_find, "find")
    inject(LuaStyleWrapper, "styles")


lua = LuaRuntime(
    register_eval=False,
    register_builtins=False,
    attribute_filter=_attr_filter,
)
