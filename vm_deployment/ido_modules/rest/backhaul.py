from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
from os import path
import json
import asyncio
import functools
import concurrent.futures
from .device_info import device_info

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from device_io.wtm4000_config import WTM4000Config

VALID_DEVICE_TYPES = {"AV4100": "AV", "AV4200": "AV"}

app = APIRouter()


class BHConfigureRequest(BaseModel):
    ip_address: str
    device_type: str
    link_type: str
    local_site_name: str
    remote_site_name: str
    tx_frequency_v: str
    rx_frequency_v: str
    tx_frequency_h: str
    rx_frequency_h: str
    bandwidth: str
    modulation_min: str
    modulation_max: str
    power_min: str
    power_max: str
    password: str | None = None
    device_number: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    xpic: bool = False


def _configure_bh_sync(params: dict):
    w = WTM4000Config(**params, readonly=False)
    w.init_and_configure()
    return {
        "success": True,
        "message": "Configuration applied successfully.",
        "device_name": getattr(w, "device_name", ""),
    }


@app.get("/api/bh/running_config")
async def get_bh_running_config(ip_address: str, device_type: str, password: str | None = None):
    try:
        if VALID_DEVICE_TYPES.get(device_type) == "AV":
            params = {
                "ip_address": ip_address,
                "device_type": device_type,
                "link_type": "dummy",
                "xpic": True,
            }
            if password:
                params["password"] = password

            loop = asyncio.get_running_loop()

            w = WTM4000Config(**params, readonly=True)

            w.init_ssh()
            with concurrent.futures.ProcessPoolExecutor() as pool:
                config = await loop.run_in_executor(
                    pool,
                    functools.partial(w.get_running_config, json_conf=True, paths=True),
                )
            w.close_session()
            config = sorted(
                [
                    # Convert path/value pairs to a string similar to Aviat config files
                    f"{'no ' if x['value'] is False else ''}{x['path']}{' ' + x['value'] if not isinstance(x['value'], bool) else ''}"
                    for x in config
                ]
            )
            return "\n".join(config)

        raise ValueError("Invalid device type")

    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"{err}") from err
    except Exception as err:
        msg = str(err)
        if "login failed" in msg.lower() or "failed to log into device" in msg.lower():
            raise HTTPException(status_code=400, detail=msg) from err
        raise HTTPException(status_code=500, detail=f"{err}") from err


@app.get("/api/bh/standard_config")
async def get_bh_standard_config(link_type: str, device_type: str, xpic: bool = False):
    params = {
        "ip_address": "0.0.0.0",
        "device_type": device_type,
        "link_type": link_type,
        "xpic": xpic,
    }

    try:
        if VALID_DEVICE_TYPES.get(device_type) == "AV":
            w = WTM4000Config(**params, readonly=True)

            config = w.get_standard_config(json_conf=True, paths=True)
            config = sorted(
                [
                    f"{'no ' if x['value'] is False else ''}{x['path']}{' ' + x['value'] if not isinstance(x['value'], bool) else ''}"
                    for x in config
                ]
            )
            return "\n".join(config)

        raise ValueError("Invalid device type")
    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"{err}") from err
    except Exception as err:
        msg = str(err)
        if "Login failed" in msg:
            raise HTTPException(status_code=400, detail=msg) from err
        raise HTTPException(status_code=500, detail=f"{err}") from err


@app.get("/api/bh/device_info")
async def get_bh_device_info(
    ip_address: str, device_type: str, run_tests: bool = False, password: str | None = None
):
    try:
        result = {}
        if VALID_DEVICE_TYPES.get(device_type) == "AV":
            loop = asyncio.get_running_loop()
            with concurrent.futures.ProcessPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    functools.partial(
                        WTM4000Config.get_device_info,
                        ip_address,
                        device_type,
                        password=password,
                        run_tests=run_tests,
                    ),
                )
        else:
            raise ValueError("Invalid device type")

        # Add ping and SNMP to test results
        with concurrent.futures.ProcessPoolExecutor() as pool:
            generic_result = await loop.run_in_executor(
                pool, functools.partial(device_info, ip_address, run_tests=run_tests)
            )

            for key, value in generic_result.items():
                if isinstance(value, list) and result.get(key):
                    result[key] += value
                elif not result.get(key):
                    result[key] = value

        return result
    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"{err}") from err
    except Exception as err:
        msg = str(err)
        if "login failed" in msg.lower() or "failed to log into device" in msg.lower():
            raise HTTPException(status_code=400, detail=msg) from err
        raise HTTPException(status_code=500, detail=f"{err}") from err


@app.post("/api/bh/configure")
async def configure_bh(request: BHConfigureRequest):
    try:
        params = request.model_dump(exclude_none=True)
        if VALID_DEVICE_TYPES.get(params["device_type"]) != "AV":
            raise ValueError("Invalid device type")

        loop = asyncio.get_running_loop()
        with concurrent.futures.ProcessPoolExecutor() as pool:
            return await loop.run_in_executor(
                pool,
                functools.partial(_configure_bh_sync, params),
            )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"{err}") from err
    except Exception as err:
        msg = str(err)
        if "login failed" in msg.lower() or "failed to log into device" in msg.lower():
            raise HTTPException(status_code=400, detail=msg) from err
        raise HTTPException(status_code=500, detail=f"{err}") from err
