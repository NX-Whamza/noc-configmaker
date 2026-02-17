from fastapi import APIRouter, HTTPException
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


@app.get("/api/bh/running_config")
async def get_bh_running_config(ip_address: str, device_type: str):
    try:
        if VALID_DEVICE_TYPES.get(device_type) == "AV":
            params = {
                "ip_address": ip_address,
                "device_type": device_type,
                "link_type": "dummy",
                "xpic": True,
            }

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
        raise HTTPException(status_code=500, detail=f"{err}") from err


@app.get("/api/bh/device_info")
async def get_bh_device_info(
    ip_address: str, device_type: str, run_tests: bool = False
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
        raise HTTPException(status_code=500, detail=f"{err}") from err
