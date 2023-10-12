from __future__ import annotations

from typing import TYPE_CHECKING, Any
from lupa import LuaRuntime

from celadon import Widget
from celadon.style_map import StyleMap
from zenith import zml_alias, zml_macro

if TYPE_CHECKING:
    from .application import HttpApplication


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
    inject(_multi_find, "find")
    inject(LuaStyleWrapper, "styles")


lua = LuaRuntime(
    register_eval=False,
    register_builtins=False,
    attribute_filter=_attr_filter,
)
