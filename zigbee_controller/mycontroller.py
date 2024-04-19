from __future__ import annotations

import asyncio
from typing import cast

import modes.light_show as ls
import orjson as json
from aiomqtt import Client as MQTTClient
from const import PUBLISH_PREFIX
from mytypes import ID, Device, LampMessage, Mode, ModeABC, RemoteRequest


class MyController:  # Seen as singleton
    def __init__(self, mqtt_hostname: str, lights: list[Device], remotes: list[Device]):
        self.mqtt = MQTTClient(hostname=mqtt_hostname, port=1883, identifier="MyZip")
        self.lock = asyncio.Lock()
        self._lights = lights
        self._remotes = remotes
        self.mode: ModeABC = DefaultMode()

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
    def new_lightsID(self) -> list[ID]:
        """Returns a new list with unique ids"""
        return [l.id for l in self._lights]

    @property
    def new_remotesID(self) -> list[ID]:
        """Returns a new list with unique ids"""
        return [l.id for l in self._remotes]

    async def _publish(self, id: ID, payload: bytes) -> None:  # For type-safety
        await self.mqtt.publish(topic=f"{PUBLISH_PREFIX}/{id}/set", payload=payload, qos=1)

    async def publish_all_lights(self, message: LampMessage):
        await self.publish_selected_lights(None, message=message)

    async def publish_selected_lights(self, indices: list[int] | None, message: LampMessage):
        """None publishes to all"""
        if message:
            data = json.dumps(message)  # No need to re-dump for all lights.
            ids = (self._lights[i].id for i in indices) if indices else (i.id for i in self._lights)
            await asyncio.gather(*(self._publish(i, data) for i in ids))

    async def publish_light(self, id: ID, message: LampMessage | bytes):
        """Bytes for pre-dumped messages, for speedup"""
        if message:
            if not isinstance(message, bytes):
                message = json.dumps(message)
            await self._publish(id, message)

    async def set_state(self, mode: Mode, mode_setting: int = 0) -> None:
        try:
            match mode:
                case Mode.DEFAULT:
                    next_state = DefaultMode()
                case Mode.LIGHT_SHOW:
                    next_state = ls.LightShowMode(routine_index=mode_setting, controller=self)
                case Mode.GAME:
                    next_state = DefaultMode()
                case Mode.SITTNING:
                    next_state = DefaultMode()
            await self.mode.cancel()
            self.mode = next_state
            await self.mode.run()
        except BaseException as e:
            raise RuntimeError("Set state failed: " + str(e))


class DefaultMode(ModeABC):
    name = Mode.DEFAULT
