from client import Client, Subscriber
from mytypes import LampMessage
import json
from typing import List, Dict, Any, Union, AsyncGenerator
from dataclasses import dataclass
import time
import asyncio
from asyncio import Queue as Aqueue

LIGHTS_PATH = "lights.json"

@dataclass
class Light:
    id: str
    x: float
    y: float
    z: float

class Load_limiter:
    def __init__(self, lights: List[Light], 
                 light_min_rest: float = float("inf"), 
                 network_max_load: int = 0, 
                 network_load_time: float = 1) -> None:
                
        self.light_min_rest = light_min_rest
        self.network_max_load = network_max_load
        self.network_load_time = network_load_time
        now = time.time()
        self.network_accessed = Aqueue(network_max_load)
        self.last_acces: dict[Light, float]= {l:n for l,n in zip(lights, [now] * len(lights))}
        self.acces_history = asyncio.Queue()
        self.task_shield = set()  # Prevent tasks from disappearing

    def light_ready(self, light: Light):
        return time.time() - self.last_acces[light] > self.light_min_rest
    
    def is_accesable(self, light: Light) -> bool:
        return self.light_ready(light) and not self.acces_history.full()
    
    async def get_in_time(self):
        await asyncio.sleep(self.network_load_time)
        await self.acces_history.get()

    async def wait_untill_accessable(self, light: Light):

        dif = self.light_min_rest - (time.time() - self.last_acces[light])
        await asyncio.sleep(dif)
        await self.acces(light)
        



    async def acces(self, light: Light):
        now = time.time()
        self.last_acces[light] = now
        self.acces_history.put_nowait(None)
        task = asyncio.create_task(self.get_in_time())
        self.task_shield.add(task)
        task.add_done_callback(self.task_shield.discard)




class IKEA_light_client:
    def __init__(self, client: Client, limiter: Load_limiter) -> None:
        self.client: Client = client
        self.limiter = limiter
        self.lights: List[Light] = self.load_lights()
    def load_lights(self) -> List[Light]:
        with open(LIGHTS_PATH, "r") as file:
            return [Light(*d) for d in json.load(file)]
        
    def add_lights(self, lights : Union[Light, List[Light]]):
        with open(LIGHTS_PATH, "r") as file:
            old_lights: List[Light] = [Light(*d) for d in json.load(file)]

        if isinstance(lights, Light):
            lights = [lights]
        old_lights.extend(lights)
        with open(LIGHTS_PATH, "w") as file:
            json.dump([d.__dict__ for d in old_lights], file)

    async def publish_asap(self, id: str, payload: Union[bytes, Dict[str, Any]]):
        self.limiter
            
    
    async def _publish(self, id: str, payload: Union[bytes, Dict[str, Any]]) -> None:  # For type-safety
        if not isinstance(payload, bytes):
            payload = json.dumps(payload).encode('utf-8')
        await self.client.publish(topic=f"{id}/set", payload=payload)


 
