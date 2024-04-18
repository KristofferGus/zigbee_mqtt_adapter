from __future__ import annotations

import asyncio
import tomllib
from dataclasses import dataclass
from typing import TypedDict, cast

import Modes.light_show as ls
import orjson as json
from aiomqtt import Client as MQTTClient
from const import COLOR_CONVERTER, PUBLISH_PREFIX
from mytypes import (
    ID,
    UINT8,
    ConfigFile,
    Device,
    LampMessage,
    Mode,
    RemoteRequest,
    XYColor,
)


class MyController:  # Seen as singleton
    def __init__(self, mqtt_hostname: str, lights: list[Device], remotes: list[Device]):
        self.mqtt = MQTTClient(hostname=mqtt_hostname, port=1883, identifier="MyZip")
        self.lock = asyncio.Lock()
        self._lights = lights
        self._remotes = remotes
        self.mode: ls.LightShowMode | DefaultMode = DefaultMode()

    async def __remote_listener(self):  # Actual remotes, always running.
        task_shield = set()  # Prevent tasks from disappearing
        unique_id_to_index = {x.id: i for i, x in enumerate(self._remotes)}
        async for msg in self.mqtt.messages:
            if self._remotes:  # Ignore if there are no remotes
                message: RemoteRequest = json.loads(cast(bytes, msg.payload))
                unique_id = msg.topic.value.split("/")[1]
                remote_index = unique_id_to_index[unique_id]
                task = asyncio.create_task(self.mode.remote_callback(message, remote_index))
                task_shield.add(task)
                task.add_done_callback(task_shield.discard)

    async def init_run(self):
        event = asyncio.Event()

        async def _mqtt_runner(mqtt: MQTTClient):
            async with mqtt:
                event.set()
                await asyncio.Future()

        self.__mqtt_conn = asyncio.create_task(_mqtt_runner(self.mqtt))  # Keep a reference, else disconnect.
        await event.wait()

        await self.set_state(Mode.DEFAULT)
        for remote in self._remotes:
            await self.mqtt.subscribe(topic=f"{PUBLISH_PREFIX}/{remote.id}/#", qos=1)
        self._remote_listener_task = asyncio.create_task(self.__remote_listener())

    @property
    def lights(self) -> list[ID]:
        return [l.id for l in self._lights]

    @property
    def remotes(self) -> list[ID]:
        return [l.id for l in self._remotes]

    async def _publish(self, id: ID, payload: bytes) -> None:  # For type-safety
        await self.mqtt.publish(topic=f"{PUBLISH_PREFIX}/{id}/set", payload=payload, qos=1)

    async def publish_all_lights(self, message: LampMessage):
        data = json.dumps(message)  # No need to re-dump for all lights.
        await asyncio.gather(*(self._publish(l.id, data) for l in self._lights))

    async def publish_light(self, id: ID, message: LampMessage | bytes):
        """Bytes for pre-dumped messages, for speedup"""
        if isinstance(message, bytes):
            await self._publish(id, message)
        else:
            await self._publish(id, json.dumps(message))

    async def set_state(self, mode: Mode, mode_setting: int = 0) -> None | str:
        try:
            match mode:
                case Mode.DEFAULT:
                    next_state = DefaultMode()
                case Mode.LIGHT_SHOW:
                    next_state = ls.LightShowMode(setting=mode_setting, controller=self)
                case Mode.GAME:
                    next_state = DefaultMode()
                case Mode.SITTNING:
                    next_state = DefaultMode()
            await self.mode.cancel()
            self.mode = next_state
            await self.mode.run()
            return None
        except BaseException as e:
            raise RuntimeError("Set state failed: " + str(e))


@dataclass
class DefaultMode:
    name = Mode.DEFAULT

    async def run(self) -> None:
        pass

    async def remote_callback(self, message: RemoteRequest, remote_index: int) -> None:
        """Remote index gives you an interface to simply track remotes by their index instead of real id, can be useful"""

    async def cancel(self) -> None:
        pass


"""
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

"""
Functions
"""


def RGB_to_XY(r: UINT8, g: UINT8, b: UINT8) -> XYColor:
    x, y = COLOR_CONVERTER.rgb_to_xy(r, g, b)
    return XYColor(x=x, y=y)


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
