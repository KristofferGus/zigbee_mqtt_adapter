from __future__ import annotations

from const import OK
from litestar import get, post
from litestar.connection import ASGIConnection
from litestar.controller import Controller
from litestar.exceptions import ClientException
from litestar.handlers.base import BaseRouteHandler
from mycontroller import MyController
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
    controller: MyController = await connection.app.dependencies["controller"]()
    if controller.mode.name != Mode.DEFAULT:
        raise ClientException("Only allowed during *Default* state, reset or change first")


class RootRouter(Controller):
    @get(
        path="/",
        description=gen_description(
            "Returns json with Keys: 'light', 'remotes', 'states'",
            "light/remote-value: list of valid ids",
            "state-value: dict of index and their given name, index should be used",
        ),
    )
    async def root(self, controller: MyController) -> dict[str, list[str] | dict[int, str]]:
        return {
            "lights": controller.new_lightsID,
            "remotes": controller.new_remotesID,
            "states": {x.value: x.name for x in Mode},
        }

    @get(path="/on", status_code=200, description="Turns state on")
    async def on(self, controller: MyController) -> str:
        async with controller.lock:
            await controller.publish_all_lights(LampMessage(state="ON"))
        return OK

    @get(path="/off", status_code=200, description="Turns state off")
    async def off(self, controller: MyController) -> str:
        async with controller.lock:
            await controller.publish_all_lights(LampMessage(state="OFF"))
        return OK

    @get(
        path=["/reset", "/reset/{value_uint8:int}"],
        description="Resets the light to halfish brightness, if path (0-255) is given -> reset to these",
    )
    async def default_reset(self, controller: MyController, value_uint8: BRIGHTNESS_UNIT8 = 127) -> str:
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
            "If only one path is given, then use default setting of this state.",
            "Second path sets the setting of the state",
            f"Valid values of states is: {list(range(len(Mode)))}",
        ),
        raises=[ClientException],
    )
    async def state_change(self, controller: MyController, id: int, setting: int = 0) -> str:
        if not (0 <= id < len(Mode)):
            raise ClientException(f"Invalid id value: 0-{len(Mode)-1}, you gave: {id}")

        async with controller.lock:
            await controller.set_state(list(Mode)[id], setting)
        return OK

    _ldescription = gen_description(
        "ONLY Allowed during Default state; reset or change state first!",
        "index -> light starting from: door(0)->longwall-shortwall-windows(max)",
        " index uses comma separated ints: light/1,2,3 or light?index=1,2,3",
        "No index given, then all lights",
        "(st)ate: ON | OFF",
        "brightness: 0-255",
        "color: [RED_UINT8, GREEN_UINT8, BLUE_UINT8]",
        "color_temp: 250-454 (~2500k-4540k)",
    )

    @get(
        path=["/light", "light/{index:str}"],
        description=_ldescription,
        guards=[default_mode_guard],
        raises=[ClientException],
    )
    async def update_light_get(
        self,
        controller: MyController,
        index: str | None = None,
        st: LampState | None = None,
        brightness: BRIGHTNESS_UNIT8 | None = None,
        color: RGB | None = None,
        color_temp: COLORTEMP250_454 | None = None,
    ) -> str:
        await self._validate_lamp_message_publish(
            controller=controller,
            index=index,
            state=st,
            brightness=brightness,
            color=color,
            color_temp=color_temp,
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
        controller: MyController,
        message: LampApiMessage,
        index: str | None = None,
    ) -> str:
        await self._validate_lamp_message_publish(controller=controller, index=index, **message)
        return OK

    """
    Utils for routing
    """

    @staticmethod
    async def _validate_lamp_message_publish(
        controller: MyController,
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
