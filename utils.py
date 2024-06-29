from __future__ import annotations
from typing import TypedDict

from typing import TypeVar, Generic, List, Dict, Tuple, Awaitable, Coroutine, Callable, Any, Generator, AsyncContextManager, Protocol
import asyncio
import json


subable_T = TypeVar("subable_T", )
sub_args = TypeVar("sub_args", contravariant=True)
unsub_args = TypeVar("unsub_args", contravariant=True)
class Subscribable(Generic[subable_T, sub_args, unsub_args], Protocol):
    def __init__(self) -> None:
        super().__init__()
    async def subscribe(self, sub: Subscriber[subable_T], args: sub_args) -> None:
        pass
    async def unsubscribe(self, sub: Subscriber[subable_T], args: unsub_args) -> None:
        pass


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
    def get_untill_empty(self) -> Generator[sub_T, None,  None]:
        while not self._call_items.empty():
            yield self._call_items.get_nowait()


load_type = TypeVar("load_type")
class Load_limiter(Generic[load_type]):
    def __init__(self, objects: List[load_type], 
                 object_min_rest: float,            #the minimum time bwteen acceses on indeviudal objects
                 network_max_load: int,             #max number of accesses on the network
                 network_load_time: float           #the duration of a network access
                 ) -> None:
                
        self.object_min_rest = object_min_rest 
         
        self.network_load_time = network_load_time 
        self.network_locks: asyncio.Semaphore = asyncio.Semaphore(network_max_load)
        self.object_locks: Dict[load_type, asyncio.Lock]= {
            l:asyncio.Lock() for l in objects}
     
        self.task_shield = set()  # Prevent tasks from disappearing



   
    
    


        
    async def acces(self, object: load_type):
        object_lock = self.object_locks[object]
        await object_lock.acquire() #Aquire object
        await self.network_locks.acquire()


        #Takes a network capacity spot for network_load_time seconds
        async def callback_in_time(time: float, func: Callable[[], Any] ):
            await asyncio.sleep(time)
            result = func()
            if type(result) == Coroutine:
                await result
        object_lock.release()
        release_object = asyncio.create_task(
            callback_in_time(self.object_min_rest, object_lock.release))
        release_network = asyncio.create_task(
            callback_in_time(self.network_load_time, self.network_locks.release))
        
        self.task_shield.add(release_object)
        release_object.add_done_callback(self.task_shield.discard)
        self.task_shield.add(release_network)
        release_network.add_done_callback(self.task_shield.discard)
        
def dict2bytes(d: Dict) -> bytes:
    return json.dumps(d).encode('utf-8')



sub_AsyncContextManager = TypeVar("sub_AsyncContextManager", bound=AsyncContextManager)
class MultiACM(AsyncContextManager, Generic[sub_AsyncContextManager]):
    def __init__(self, resources: List[sub_AsyncContextManager]):
        self.resources: List[sub_AsyncContextManager] = resources

    async def __aenter__(self):
        self.active_resources = await asyncio.gather(*[resource.__aenter__() for resource in self.resources])
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await asyncio.gather(*[resource.__aexit__(exc_type, exc, tb) for resource in self.resources])


