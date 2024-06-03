from __future__ import annotations

import asyncio
from typing import Callable, Dict, List, Generic, TypeVar, Coroutine, Generator
from aiomqtt import Client as MQTTClient, Message



sub_T = TypeVar("sub_T")
class Subscriber(Generic[sub_T]):
    def __init__(self, max_itmes: int = 0) -> None:
        self._call_items: asyncio.Queue[sub_T] = asyncio.Queue(max_itmes)
    async def call_back(self, t: sub_T):
        if self._call_items.full():
            self._call_items.get_nowait()
        self._call_items.put_nowait(t)
    async def get_item(self) -> sub_T:
        return await self._call_items.get()
    def get_untill_empty(self) -> Generator:
        while not self._call_items.empty():
            yield self._call_items.get_nowait()


class Client: 
    def __init__(self, mqtt_hostname: str, topic_prefix: str = "", port: int = 1883,
                 identifier: str ="MyZip") -> None:
        self.prefix = topic_prefix
        self.mqtt = MQTTClient(hostname=mqtt_hostname, port=port, identifier=identifier)
        self.subbed_topics: Dict[str, List[Subscriber[Message]]] = {}
    

    
            

    async def sub_topic(self, topic: str,subscriber: Subscriber[Message]) -> None:
        if not topic in self.subbed_topics.keys():
            await self.mqtt.subscribe(topic= self.prefix + topic, qos=1)
        topic_subs = self.subbed_topics.get(topic, [])
        topic_subs.append(subscriber)
        self.subbed_topics[topic] = topic_subs

    
    async def unsub_topic(self, topic: str,subscriber: Subscriber[Message]) -> None:
        topic_subs = self.subbed_topics.get(topic, None)

        if topic_subs != None:
            try:
                topic_subs.remove(subscriber)
            except ValueError:
                pass
            if len(topic_subs) == 0:
                del self.subbed_topics[topic]
                await self.mqtt.unsubscribe(topic= self.prefix + topic)

        
    

    async def __listen(self):  # Actual remotes, always running.
        task_shield = set()  # Prevent tasks from disappearing
        async for msg in self.mqtt.messages:
            subscribers = self.subbed_topics[msg.topic.value]
            tasks = [asyncio.create_task(sub.call_back(msg)) for sub in subscribers]
            for task in tasks:
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
        self._remote_listener_task = asyncio.create_task(self.__listen())



  

    async def publish(self, topic: str, payload: bytes) -> None:  # For type-safety
        await self.mqtt.publish(topic=self.prefix + topic, payload=payload, qos=1)

    async def get_pub(self, topic:str, payload: bytes) -> Message:
        sub = Subscriber()
        await self.sub_topic(topic, sub)
        await self.publish(topic, payload)
        message = await sub.get_item()
        await self.unsub_topic(topic, sub)
        return message


