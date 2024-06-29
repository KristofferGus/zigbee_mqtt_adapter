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
        clinet = DeviceClient(fc)
        friendly_name = "0x0c4314fffe19426b"
        async with DualDevice[bytes, Message](
                            friendly_name=friendly_name, 
                            communicator=clinet,
                            read_topics={""}
                            ) as device:
            while True:
                await device.send_to(topic="get",
                            payload=dict2bytes({"battery": ""}))
                
                
                message = await device.recive_from(topic="")
                print("found", message.payload)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
    
