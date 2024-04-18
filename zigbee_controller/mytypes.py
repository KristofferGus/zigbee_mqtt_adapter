from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Literal, TypedDict

COLORTEMP250_454 = int  # Probably 2500k-4540k but in 250-454 range.
RED_UINT8 = GREEN_UINT8 = BLUE_UINT8 = UINT8 = UINT32 = BRIGHTNESS_UNIT8 = int
# Types
RGBI_UINT8 = tuple[RED_UINT8, GREEN_UINT8, BLUE_UINT8, BRIGHTNESS_UNIT8]
COLORS_UINT8 = list[RGBI_UINT8 | None]
RGB = tuple[RED_UINT8, GREEN_UINT8, BLUE_UINT8]
ID = str
LampState = Literal["ON", "OFF"]


@dataclass
class Device:
    id: ID


class DeviceConfig(TypedDict):
    id: ID


class ConfigFile(TypedDict):
    lights: list[DeviceConfig]
    remotes: list[DeviceConfig]  # NotRequired


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


class Mode(IntEnum):
    DEFAULT = 0
    LIGHT_SHOW = 1
    GAME = 2
    SITTNING = 3


class ModeABC(ABC):
    async def run(self) -> None: ...
    async def cancel(self) -> None: ...
    async def remote_callback(self, message: RemoteRequest, remote_index: int) -> None:
        """
        Remote index gives you an interface to simply track remotes
        by their index instead of real id, can be useful
        Example remote_callback:
            async def remote_callback(self, message: RemoteRequest, remote_index: int):
                state = ModeState.LIGHT_SHOW
                match message["action"]:
                    case RemoteAction.ON:
                        pass
                    case RemoteAction.OFF:
                        pass
                    case RemoteAction.BRIGHTESS_MOVE_UP:
                        pass
                    case RemoteAction.BRIGHTESS_MOVE_DOWN:
                        pass
                    case RemoteAction.BRIGHTESS_MOVE_STOP:
                        pass
                    case RemoteAction.ARROW_LEFT_CLICK:
                        pass
                    case RemoteAction.ARROW_LEFT_HOLD:
                        pass
                    case RemoteAction.ARROW_LEFT_RELEASE:
                        pass
                    case RemoteAction.ARROW_RIGHT_CLICK:
                        pass
                    case RemoteAction.ARROW_RIGHT_HOLD:
                        pass
                    case RemoteAction.ARROW_RIGHT_RELEASE:
                        pass
                    case _:
                        raise ValueError("Unknown remote message received")
        """


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
