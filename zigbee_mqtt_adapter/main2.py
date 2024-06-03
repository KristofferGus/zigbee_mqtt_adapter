from client import Client
from const import HOST


async def main():
    controller = Client(mqtt_hostname=HOST)
    await controller.init_run()
    controller.publish()