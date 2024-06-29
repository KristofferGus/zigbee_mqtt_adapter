
import asyncio
from typing import TypeVar, Generic, Callable, AsyncContextManager, List, Dict, Type, Coroutine, Set, Protocol
from abc import ABC, abstractmethod
from utils import Subscribable, Subscriber
class Device:
    def __init__(self, friendly_name: str) -> None:
        self.friendly_name = friendly_name

sender_type = TypeVar("sender_type", contravariant=True)
class Sender(Generic[sender_type], Protocol):
    def __init__(self) -> None:
        super().__init__()
    
    async def send(self, topic: str, payload: sender_type):
        pass


payload_type = TypeVar("payload_type")
class Reciver(Device, Generic[payload_type]):
    def __init__(self, friendly_name: str, 
                 sender: Sender[payload_type],
                 prefix: str = ""
                 ) -> None:
        super().__init__(friendly_name)
        self.prefix = f"{prefix}{"/" if prefix != "" else ""}{friendly_name}"
        
        self.sender = sender

    async def send_to(self, topic: str, payload: payload_type):
        await self.sender.send(f"{self.prefix}/{topic}", payload)




publisher_recive_T = TypeVar("publisher_recive_T")


class Publisher(Device, AsyncContextManager, Generic[publisher_recive_T]):
    def __init__(self, friendly_name: str, 
                 informer: Subscribable[publisher_recive_T, str, str],
                 read_topics: Set[str],
                 prefix: str = ""
                 ) -> None:
        super().__init__(friendly_name)
        self._subscribers: Dict[str, Subscriber[publisher_recive_T]] = {}
        self._informer: Subscribable[publisher_recive_T, str, str] = informer
        self._publish_topics: Set[str] = read_topics
        
        self.prefix = f"{prefix}{"/" if prefix != "" else ""}{friendly_name}"

    async def __aenter__(self):
        tasks = []
        for topic in self._publish_topics:
            sub = Subscriber[publisher_recive_T]()
            self._subscribers[topic] = sub
            tasks.append(self._informer.subscribe(sub, 
                                                  f"{self.prefix}{"/" if topic != "" else ""}{topic}"))
        await asyncio.gather(*tasks)
        return self
    
    async def recive_from(self, topic: str | None = None) -> publisher_recive_T:

        if topic is None:
            topic = list(self._publish_topics)[0]
        elif not (topic in self._publish_topics):
            raise Exception("Topic is not subscribed to, call could never finish")
        return await self._subscribers[topic].get_item()
        
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        tasks = []
        for topic in self._publish_topics:
            sub = self._subscribers[topic]
            tasks.append(self._informer.unsubscribe(sub, f"{self.prefix}/{topic}"))
        await asyncio.gather(*tasks)

class Communicator(Sender, Subscribable, Protocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__()

class DualDevice(Device, Generic[payload_type, publisher_recive_T], AsyncContextManager):
    def __init__(self, friendly_name: str,
                 communicator: Communicator,
                 read_topics: Set[str],
                 prefix: str = ""
                 ) -> None:
        super().__init__(friendly_name)
        
        self._reciver = Reciver[payload_type](friendly_name, communicator, prefix)
        self._publisher = Publisher[publisher_recive_T](friendly_name, communicator, read_topics, prefix)

    async def send_to(self, topic: str, payload: payload_type):
        await self._reciver.send_to(topic, payload)
        
    
    async def recive_from(self, topic: str | None = None) -> publisher_recive_T:
        return await self._publisher.recive_from(topic)

    async def __aenter__(self):
        await self._publisher.__aenter__()
        return self

   
    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._publisher.__aexit__(exc_type, exc_value, traceback)
        return None