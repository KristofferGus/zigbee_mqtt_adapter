from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Iterable
from typing import TYPE_CHECKING

import orjson as json
from mytypes import COLORS_UINT8, COLORTEMP250_454, ID, RGBI_UINT8, LampMessage
from utils import RGB_to_XY

if TYPE_CHECKING:
    from utils import MyController


def gen_lamp_message(colors: RGBI_UINT8 | None, color_temp: COLORTEMP250_454 = 250) -> LampMessage:
    if not colors:
        return LampMessage(state="OFF")
    r, g, b, i = colors
    return LampMessage(state="ON", brightness=i, color=RGB_to_XY(r, g, b), color_temp=color_temp)


async def publish_apply_mapping(
    controller: MyController,
    lights: Iterable[ID],
    mapping_message: list[bytes] | list[LampMessage],
):
    await asyncio.gather(*(controller.publish_light(id, rc) for id, rc in zip(lights, mapping_message)))


async def _rotate_lights_1step(
    controller: MyController,
    lights: list[ID],
    colors_mapping: COLORS_UINT8,
    sleep: float = 0.5,
    clockwise: bool = False,
):
    # Mapping, store as dump to reduce re-dumping.
    color_mapping_message = [json.dumps(gen_lamp_message(rgbi)) for rgbi in colors_mapping]
    if clockwise:
        color_mapping_message.reverse()

    new_lights = deque(lights)
    while True:
        await publish_apply_mapping(controller=controller, lights=new_lights, mapping_message=color_mapping_message)
        if clockwise:
            new_lights.append(new_lights.popleft())
        else:
            new_lights.appendleft(new_lights.pop())
        await asyncio.sleep(sleep)


async def circle_rainbow_fade(
    controller: MyController,
    lights: list[ID],
    sleep: float = 0.5,
    clockwise: bool = False,
):
    rainbow_mapping: COLORS_UINT8 = [
        (148, 0, 211, 100),
        (75, 0, 130, 80),
        (0, 0, 255, 60),
        (0, 255, 0, 50),
        (255, 255, 0, 40),
        (255, 127, 0, 30),
        (255, 0, 0, 20),
        None,
        None,
    ]
    await _rotate_lights_1step(controller, lights, rainbow_mapping, sleep=sleep, clockwise=clockwise)


async def circle_bw_fade(
    controller: MyController,
    lights: list[ID],
    sleep: float = 0.5,
    clockwise: bool = False,
):
    bw_mapping: COLORS_UINT8 = [
        (255, 255, 255, 100),
        (255, 255, 255, 80),
        (255, 255, 255, 60),
        (255, 255, 255, 50),
        (255, 255, 255, 40),
        (255, 255, 255, 30),
        (255, 255, 255, 20),
        None,
        None,
    ]
    await _rotate_lights_1step(controller, lights, bw_mapping, sleep=sleep, clockwise=clockwise)


async def every_other(controller: MyController, lights: list[ID], sleep: float = 0.5):
    other_mapping: COLORS_UINT8 = [(255, 255, 255, 120) if (i % 2) == 0 else None for i in range(len(lights))]
    await _rotate_lights_1step(controller, lights, other_mapping, sleep=sleep)
