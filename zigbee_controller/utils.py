from __future__ import annotations

import tomllib
from typing import TypedDict

from const import COLOR_CONVERTER
from mytypes import UINT8, ConfigFile, Device, XYColor

"""
Functions
"""


def RGB_to_XY(r: UINT8, g: UINT8, b: UINT8) -> XYColor:
    x, y = COLOR_CONVERTER.rgb_to_xy(r, g, b)
    return XYColor(x=x, y=y)


def gen_description(*strings: str):
    return "\n\n".join(strings)


def load_config():
    class RetType(TypedDict):
        lights: list[Device]
        remotes: list[Device]

    with open("config.toml", "rb") as f:
        cfg = ConfigFile(**tomllib.load(f))  # remotes might be missing
    return RetType(
        lights=[Device(**l) for l in cfg["lights"]],
        remotes=[Device(**r) for r in cfg.get("remotes", [])],
    )
