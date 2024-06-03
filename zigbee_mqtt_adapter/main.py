from __future__ import annotations

import uvicorn
from litestar import Litestar, get
from litestar.openapi import OpenAPIConfig, OpenAPIController
from litestar.response import Redirect
from litestar.status_codes import HTTP_301_MOVED_PERMANENTLY
from mycontroller import controller
from routing import RootRouter


class MyOpenAPIController(OpenAPIController):
    path = "/rschema"


@get(path="/schema", status_code=HTTP_301_MOVED_PERMANENTLY, include_in_schema=False)
async def redirect_schema() -> Redirect:
    """Redoc is default, no 2nd path. Other: swagger, elements, rapidoc"""
    return Redirect(path="/rschema/elements", status_code=HTTP_301_MOVED_PERMANENTLY)


async def init_controller():
    await controller.init_run()


app = Litestar(
    debug=True,
    on_startup=[init_controller],
    route_handlers=[RootRouter, redirect_schema],
    openapi_config=OpenAPIConfig(title="My API", version="0.0.1", openapi_controller=MyOpenAPIController),
)


if __name__ == "__main__":
    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=9999,
        log_level="info",
    )
