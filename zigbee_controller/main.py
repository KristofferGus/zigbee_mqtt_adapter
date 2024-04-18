from __future__ import annotations

import uvicorn
from const import HOST
from litestar import Litestar
from litestar.di import Provide
from litestar.openapi import OpenAPIConfig, OpenAPIController
from routing import RootRouter
from utils import MyController, load_config


class MyOpenAPIController(OpenAPIController):
    path = "/schema"


controller = MyController(mqtt_hostname=HOST, **load_config())


async def init_controller():
    await controller.init_run()


async def di_controller():  # Simply to reverse dependency (dependency injection)
    return controller


app = Litestar(
    debug=True,
    on_startup=[init_controller],
    route_handlers=[RootRouter],
    dependencies={"controller": Provide(di_controller)},
    openapi_config=OpenAPIConfig(title="My API", version="0.0.1", openapi_controller=MyOpenAPIController),
)


if __name__ == "__main__":
    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=9999,
        log_level="info",
    )
