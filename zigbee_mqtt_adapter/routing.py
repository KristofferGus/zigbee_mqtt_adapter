from __future__ import annotations

import orjson as json
from const import OK
from litestar import get, post
from litestar.connection import ASGIConnection
from litestar.controller import Controller
from litestar.exceptions import ClientException
from litestar.handlers.base import BaseRouteHandler
from mycontroller import controller
from mytypes import (
    BRIGHTNESS_UNIT8,
    COLORTEMP250_454,
    RGB,
    LampApiMessage,
    LampMessage,
    LampState,
    Mode,
)
from utils import RGB_to_XY, gen_description


async def default_mode_guard(connection: ASGIConnection, handler: BaseRouteHandler) -> None:
    if controller.mode.name != Mode.DEFAULT:
        raise ClientException("Only allowed during *Default* state, reset or change first")


class RootRouter(Controller):
    @get(
        path="/",
        description=gen_description(
            "Returns json with Keys: **'light', 'remotes', 'states'**",
            "\tlight/remote-value: list[ID(str)]",
            f"\tmode-value: {dict((str(x.value), x.name) for x in Mode)} // Real result",
        ),
    )
    async def root(self) -> dict[str, list[str] | dict[int, str]]:
        return {
            "lights": controller.new_lightsID,
            "remotes": controller.new_remotesID,
            "mode": {x.value: x.name for x in Mode},
        }

    @get(path="/on", status_code=200, description="Turns state **on**")
    async def on(self) -> str:
        async with controller.lock:
            await controller.publish_all_lights(LampMessage(state="ON"))
        return OK

    @get(path="/off", status_code=200, description="Turns state **off**")
    async def off(self) -> str:
        async with controller.lock:
            await controller.publish_all_lights(LampMessage(state="OFF"))
        return OK

    @get(
        path=["/reset", "/reset/{value_uint8:int}"],
        description="Resets the light to halfish brightness, if path **(0-255)** is given -> reset to these",
    )
    async def default_reset(self, value_uint8: BRIGHTNESS_UNIT8 = 127) -> str:
        async with controller.lock:
            message = LampMessage(
                state="ON",
                brightness=min(255, max(0, value_uint8)),
                color=RGB_to_XY(255, 255, 255),
                color_temp=300,
            )
            await controller.set_state(Mode.DEFAULT)
            await controller.publish_all_lights(message)
        return OK

    @get(
        path=["/state/{id:int}", "/state/{id:int}/{setting:int}"],
        description=gen_description(
            "If only one path is given, then use default setting of this mode.",
            "Second path sets the setting of the state",
            f"Mapping: **{dict((x.value, x.name) for x in Mode)}**",
            f"\tid: {list(range(len(Mode)))}",
        ),
        raises=[ClientException],
    )
    async def state_change(self, id: int, setting: int = 0) -> str:
        if not (0 <= id < len(Mode)):
            raise ClientException(f"Invalid id value: 0-{len(Mode)-1}, you gave: {id}")

        async with controller.lock:
            await controller.set_state(list(Mode)[id], setting)

        return OK

    _ldescription = gen_description(
        "### ONLY Allowed during Default state; reset or change state first!",
        f"index **(0-{len(controller._lights)-1})** -> light starting from: "
        f"door(**0**)->longwall-shortwall-windows(**{len(controller._lights)-1}**)",
        " index uses comma separated ints: **light/1 | light/0,2,3 | light?index=1,2,3**",
        "***No index given, then all lights***",
        "\t(st)ate: ON | OFF | null",
        "\tbrightness: 0-255",
        "\tcolor: [RED_UINT8, GREEN_UINT8, BLUE_UINT8]",
        "\tcolor_temp: 250-454 (~2500k-4540k)",
    )

    @get(
        path=["/light", "light/{index:str}"],
        description=_ldescription,
        guards=[default_mode_guard],
        raises=[ClientException],
    )
    async def update_light_get(
        self,
        index: str | None = None,
        st: LampState | None = None,
        brightness: BRIGHTNESS_UNIT8 | None = None,
        color: str | None = None,
        color_temp: COLORTEMP250_454 | None = None,
    ) -> str:
        if color:
            try:
                r, g, b = map(int, json.loads(color))
                _color = (r, g, b)
            except:
                raise ClientException("Too few/many colors given or not an int")
        else:
            _color = None
        await self._validate_lamp_message_publish(
            index=index, state=st, brightness=brightness, color=_color, color_temp=color_temp
        )
        return OK

    @post(
        path=["/light", "light/{index:str}"],
        description=_ldescription,
        guards=[default_mode_guard],
        raises=[ClientException],
    )
    async def update_light_post(
        self,
        message: LampApiMessage,
        index: str | None = None,
    ) -> str:
        await self._validate_lamp_message_publish(index=index, **message)
        return OK

    """
    Utils for routing
    """

    @staticmethod
    async def _validate_lamp_message_publish(
        index: str | None,
        state: LampState | None = None,
        brightness: BRIGHTNESS_UNIT8 | None = None,
        color: RGB | None = None,
        color_temp: COLORTEMP250_454 | None = None,
    ):
        indices: list[int] | None = None
        if index is not None:
            indices = list(map(int, index.split(",")))
            _num_lights = len(controller._lights)
            if not (indices and len(set(indices)) == len(indices) and all(0 <= i < _num_lights for i in indices)):
                raise ClientException(f"Invalid/duplicate index selected, select a value between 0-{_num_lights}")

        message = LampMessage()
        if state:
            message["state"] = state

        if brightness:
            if not (0 <= brightness <= 255):
                raise ClientException("Invalid brightness value: 0-255")
            message["brightness"] = brightness

        if color:
            if not (len(color) == 3 and all(0 <= x <= 255 for x in color)):
                raise ClientException(f"Invalid color value: 0-255, you gave: {color}")
            message["color"] = RGB_to_XY(*color)

        if color_temp:
            if not (250 <= color_temp <= 454):
                if 2500 <= color_temp <= 4549:  # If user thinks 2500k!
                    color_temp = int(color_temp // 10)
                else:
                    raise ClientException(f"Invalid color_temp value: 250-454 | 2500-4540, you gave: {color_temp}")
            message["color_temp"] = color_temp

        async with controller.lock:
            await controller.publish_selected_lights(indices=indices, message=message)
