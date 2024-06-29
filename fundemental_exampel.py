from client_mqtt import *
import asyncio
import json
from mqttDevices import DualDevice
from utils import dict2bytes
import os
PUBLISH_PREFIX = "zigbee2mqtt"
HOST = os.environ.get("MQTT_ADDR", "localhost")



async def main():
    async with FundementalClient(HOST, PUBLISH_PREFIX,verbose=True) as fc:
        
        friendly_name = "0x0c4314fffe19426b"
        sub = Subscriber[Message]()
        await fc.sub_topic(friendly_name, sub)
        while True:
            await fc.publish(f"{friendly_name}/get", dict2bytes({"battery": ""}))
            message = await sub.get_item()
            print(message.payload)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
    
