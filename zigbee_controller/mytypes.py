from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Literal, TypedDict

COLORTEMP250_454 = int  # Probably 2500k-4540k but in 250-454 range.
RED_UINT8 = GREEN_UINT8 = BLUE_UINT8 = UINT8 = UINT32 = BRIGHTNESS_UNIT8 = int
# Types
COLORS_UINT8 = list[tuple[RED_UINT8, GREEN_UINT8, BLUE_UINT8, BRIGHTNESS_UNIT8] | None]
RGB = tuple[RED_UINT8, GREEN_UINT8, BLUE_UINT8]
Id = str
LampState = Literal["ON", "OFF"]


class DeviceConfig(TypedDict):
    id: Id


class ConfigFile(TypedDict):
    lights: list[DeviceConfig]
    remotes: list[DeviceConfig] # NotRequired


class XYColor(TypedDict):
    x: float
    y: float


class LampMessage(TypedDict, total=False):
    state: LampState
    brightness: BRIGHTNESS_UNIT8
    color: XYColor
    color_temp: COLORTEMP250_454


class RemoteRequest(TypedDict):
    action: RemoteAction
    link_quality: UINT32


class LampApiMessage(TypedDict, total=False):
    state: LampState
    brightness: BRIGHTNESS_UNIT8
    color: tuple[RED_UINT8, GREEN_UINT8, BLUE_UINT8]
    color_temp: COLORTEMP250_454


class ModeState(IntEnum):
    DEFAULT = 0
    LIGHT_SHOW = 1
    GAME = 2
    SITTNING = 3


class RemoteAction(StrEnum):
    ON = "on"
    OFF = "off"
    BRIGHTESS_MOVE_UP = "brightness_move_up"
    BRIGHTESS_MOVE_DOWN = "brightness_move_down"
    BRIGHTESS_MOVE_STOP = "brightness_stop"
    ARROW_LEFT_CLICK = "arrow_left_click"
    ARROW_LEFT_HOLD = "arrow_left_hold"
    ARROW_LEFT_RELEASE = "arrow_left_release"
    ARROW_RIGHT_CLICK = "arrow_right_click"
    ARROW_RIGHT_HOLD = "arrow_right_hold"
    ARROW_RIGHT_RELEASE = "arrow_right_release"
