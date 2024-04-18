from __future__ import annotations

import asyncio
from collections import deque
from typing import TYPE_CHECKING

from mytypes import COLORS_UINT8, DeviceConfig, LampMessage
from utils import RGB_to_XY

if TYPE_CHECKING:
    from utils import MyController


async def _circle_fade(
    controller: MyController,
    lights: list[DeviceConfig],
    colors: COLORS_UINT8,
    sleep: float = 0.5,
    cw: bool = False,
):
    lamp_fac = lambda r, g, b, i: LampMessage(
        state="ON",
        brightness=i,
        color=RGB_to_XY(r, g, b),
        color_temp=50,
    )
    new_lights = deque([x["id"] for x in lights])  # Copy
    fading_colors = [lamp_fac(*rgbi) if rgbi else LampMessage(state="OFF") for rgbi in colors]

    if cw:
        fading_colors.reverse()
    while True:
        await asyncio.gather(*(controller.publish_light(addr, rc) for addr, rc in zip(new_lights, fading_colors)))
        if cw:
            new_lights.append(new_lights.popleft())
        else:
            new_lights.appendleft(new_lights.pop())
        await asyncio.sleep(sleep)


async def circle_rainbow_fade(
    controller: MyController,
    lights: list[DeviceConfig],
    sleep: float = 0.5,
    cw: bool = False,
):
    rainbow_colors = [
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
    await _circle_fade(controller, lights, rainbow_colors, sleep=sleep, cw=cw)


async def circle_bw_fade(
    controller: MyController,
    lights: list[DeviceConfig],
    sleep: float = 0.5,
    cw: bool = False,
):
    bw_colors = [
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
    await _circle_fade(controller, lights, bw_colors, sleep=sleep, cw=cw)


async def every_other(controller: MyController, lights: list[DeviceConfig], sleep: float = 0.5):
    other_colors: COLORS_UINT8 = [(255, 255, 255, 120) if (i % 2) == 0 else None for i in range(len(lights))]
    await _circle_fade(controller, lights, other_colors, sleep=sleep)
