import json
from fastapi import APIRouter, HTTPException, Request

from .mt_config_gen.mt_tower import MTTowerConfig
from .mt_config_gen.mt_bng2 import MTBNG2Config

CONFIG_TYPES = {"tower": MTTowerConfig, "bng2": MTBNG2Config}

app = APIRouter()


@app.post("/api/mt/{config_type}/config")
async def post_config(config_type: str, request: Request):
    try:
        config = CONFIG_TYPES.get(config_type)
        if not config:
            raise HTTPException(
                status_code=400, detail=f"Invalid config type: {config_type}"
            )

        body = await request.body()
        body_str = body.decode("utf-8")

        data = json.loads(body_str)

        m = config(**data)
        return m.generate_config()

    except Exception as err:
        raise HTTPException(status_code=500, detail=f"{err}") from err


@app.post("/api/mt/{config_type}/portmap")
async def post_port_map(config_type: str, request: Request):
    try:
        config = CONFIG_TYPES.get(config_type)
        if not config:
            raise HTTPException(
                status_code=400, detail=f"Invalid config type: {config_type}"
            )

        body = await request.body()
        body_str = body.decode("utf-8")

        data = json.loads(body_str)

        m = config(**data)
        return m.generate_port_map()

    except Exception as err:
        raise HTTPException(status_code=500, detail=f"{err}") from err
