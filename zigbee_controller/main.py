from __future__ import annotations

import uvicorn
from const import HOST
from litestar import Litestar, get
from litestar.di import Provide
from litestar.openapi import OpenAPIConfig, OpenAPIController
from litestar.response import Redirect
from litestar.status_codes import HTTP_301_MOVED_PERMANENTLY
from mycontroller import MyController
from routing import RootRouter
from utils import load_config


class MyOpenAPIController(OpenAPIController):
    path = "/rschema"


@get(path="/schema", status_code=HTTP_301_MOVED_PERMANENTLY, include_in_schema=False)
async def redirect_schema() -> Redirect:
    """Redoc is default, no 2nd path. Other: swagger, elements, rapidoc"""
    return Redirect(path="/rschema/elements", status_code=HTTP_301_MOVED_PERMANENTLY)


controller = MyController(mqtt_hostname=HOST, **load_config())


async def init_controller():
    await controller.init_run()


async def di_controller():  # Simply to reverse dependency (dependency injection)
    return controller


app = Litestar(
    debug=True,
    on_startup=[init_controller],
    route_handlers=[RootRouter, redirect_schema],
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
