from rgbxy import Converter
import os

COLOR_CONVERTER = Converter()
PUBLISH_PREFIX = "zigbee2mqtt"
HOST = os.environ.get("MQTT_ADDR", "localhost")
OK = "OK"
