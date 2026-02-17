from fastapi import APIRouter, HTTPException
import sys
from os import path
import json
import asyncio
import functools
import concurrent.futures
import logging
from .device_info import device_info

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from device_io.epmp_config import EPMPConfig
from device_io.tachyon_config import TachyonConfig
from device_io.wave_config import WaveConfig


def get_cambium_running_config(ip_address: str, device_type: str, password: str | None = None):
    params = {"ip_address": ip_address, "device_type": device_type, "use_default": True}
    if password:
        params["password"] = password
    d = EPMPConfig(**params)
    d.init_session()
    config = d.get_running_config()
    d.logout()
    return config


def get_cambium_standard_config(device_type: str, ip_address: str = "0.0.0.0", password: str | None = None):
    params = {"ip_address": f"{ip_address}", "device_type": device_type, "use_default": True}
    if password:
        params["password"] = password
    d = EPMPConfig(**params)
    return d.get_standard_config(stripped=True, json_conf=True)


def get_cambium_device_info(ip_address: str, device_type: str, run_tests: bool = False, password: str | None = None):
    return EPMPConfig.get_device_info(ip_address, device_type, password=password, run_tests=run_tests)


def get_tachyon_running_config(ip_address: str, device_type: str, password: str | None = None):
    params = {"ip_address": ip_address, "device_type": device_type, "readonly": True}
    if password:
        params["password"] = password
    d = TachyonConfig(**params)
    d.init_session()
    config = d.get_running_config(paths=True)
    d.logout()
    config = sorted([f"{x['path']}: {json.dumps(x['value'])}" for x in config])
    return "\n".join(config)


def get_tachyon_standard_config(device_type: str, ip_address: str = "0.0.0.0", password: str | None = None):
    params = {"ip_address": f"{ip_address}", "device_type": device_type, "readonly": True}
    if password:
        params["password"] = password
    d = TachyonConfig(**params)

    config = d.get_standard_config()
    config = sorted([f"{x['path']}: {json.dumps(x['value'])}" for x in config])
    return "\n".join(config)


def get_tachyon_device_info(ip_address: str, device_type: str, run_tests: bool = False, password: str | None = None):
    return TachyonConfig.get_device_info(ip_address, device_type, password=password, run_tests=run_tests)

def get_wave_running_config(ip_address: str, device_type: str, password: str | None = None):
    config = WaveConfig.get_device_info(ip_address, device_type.split("UB")[1], password=password, run_tests=False)
    return config.get("running_config")

def get_wave_standard_config(device_type: str, ip_address: str = "0.0.0.0", password: str | None = None):
    config = WaveConfig.get_device_info(f"{ip_address}", device_type.split("UB")[1], password=password, run_tests=False)
    return config.get("standard_config")

def get_wave_device_info(ip_address: str, device_type: str, run_tests: bool = False, password: str | None = None):
    return WaveConfig.get_device_info(ip_address, device_type.split("UB")[1], password=password, run_tests=run_tests)

VALID_DEVICE_TYPES = {
    "CNEP3K": "CN",
    "CN4600": "CN",
    "CNF300-13": "CN",
    "CNF300-16": "CN",
    "CNF300-25": "CN",
    "CNF300-CSM": "CN",
    "TYN301": "TY",
    "TYN302": "TY",
    "UBWAP": "UB",
    "UBWAPM": "UB",
}

app = APIRouter()


@app.get("/api/ap/running_config")
async def get_ap_running_config(ip_address: str, device_type: str, password: str | None = None):
    oem = VALID_DEVICE_TYPES.get(device_type)

    loop = asyncio.get_running_loop()

    try:
        if oem == "CN":
            with concurrent.futures.ProcessPoolExecutor() as pool:
                return await loop.run_in_executor(
                    pool,
                    functools.partial(
                        get_cambium_running_config,
                        ip_address=ip_address,
                        device_type=device_type,
                        password=password,
                    ),
                )
        if oem == "TY":
            with concurrent.futures.ProcessPoolExecutor() as pool:
                return await loop.run_in_executor(
                    pool,
                    functools.partial(
                        get_tachyon_running_config,
                        ip_address=ip_address,
                        device_type=device_type,
                        password=password,
                    ),
                )
        if oem == "UB":
            with concurrent.futures.ProcessPoolExecutor() as pool:
                return await loop.run_in_executor(
                    pool,
                    functools.partial(
                        get_wave_running_config,
                        ip_address=ip_address,
                        device_type=device_type,
                        password=password,
                    ),
                )

        raise ValueError("Invalid device type")

    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"{err}") from err
    except Exception as err:
        msg = str(err)
        if "invalid response while logging in" in msg.lower() or "login failed" in msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Device login failed while fetching running config. Verify AP credentials/default passwords and that the target is a supported Cambium/Tachyon/Wave AP.",
            ) from err
        raise HTTPException(status_code=500, detail=f"{err}") from err


@app.get("/api/ap/standard_config")
async def get_ap_standard_config(ip_address: str, device_type: str, password: str | None = None):
    oem = VALID_DEVICE_TYPES.get(device_type)

    loop = asyncio.get_running_loop()

    try:
        if oem == "CN":
            with concurrent.futures.ProcessPoolExecutor() as pool:
                return await loop.run_in_executor(
                    pool,
                    functools.partial(
                        get_cambium_standard_config,
                        ip_address=ip_address,
                        device_type=device_type,
                        password=password,
                    ),
                )
        if oem == "TY":
            with concurrent.futures.ProcessPoolExecutor() as pool:
                return await loop.run_in_executor(
                    pool,
                    functools.partial(
                        get_tachyon_standard_config,
                        ip_address=ip_address,
                        device_type=device_type,
                        password=password,
                    ),
                )
        if oem == "UB":
            with concurrent.futures.ProcessPoolExecutor() as pool:
                return await loop.run_in_executor(
                    pool,
                    functools.partial(
                        get_wave_standard_config,
                        ip_address=ip_address,
                        device_type=device_type,
                        password=password,
                    ),
                )


        raise ValueError("Invalid device type")

    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"{err}") from err
    except Exception as err:
        msg = str(err)
        if "invalid response while logging in" in msg.lower() or "login failed" in msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Device login failed while fetching standard config. Verify AP credentials/default passwords and that the target is a supported Cambium/Tachyon/Wave AP.",
            ) from err
        raise HTTPException(status_code=500, detail=f"{err}") from err


@app.get("/api/ap/device_info")
async def get_ap_device_info(
    ip_address: str, device_type: str, run_tests: bool = False, password: str | None = None
):
    oem = VALID_DEVICE_TYPES.get(device_type)

    loop = asyncio.get_running_loop()

    try:
        result = {}
        if oem == "CN":
            with concurrent.futures.ProcessPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    functools.partial(
                        get_cambium_device_info,
                        ip_address=ip_address,
                        device_type=device_type,
                        password=password,
                        run_tests=run_tests,
                    ),
                )
        elif oem == "TY":
            with concurrent.futures.ProcessPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    functools.partial(
                        get_tachyon_device_info,
                        ip_address=ip_address,
                        device_type=device_type,
                        password=password,
                        run_tests=run_tests,
                    ),
                )
        elif oem == "UB":
            with concurrent.futures.ProcessPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    functools.partial(
                        get_wave_device_info,
                        ip_address=ip_address,
                        device_type=device_type,
                        password=password,
                        run_tests=run_tests
                    ),
                )

        else:
            raise ValueError("Invalid device type")

        # Add ping and SNMP to test results
        with concurrent.futures.ProcessPoolExecutor() as pool:
            generic_result = await loop.run_in_executor(
                pool, functools.partial(device_info, ip_address, run_tests=run_tests)
            )

            # For APs, the SNMP name should be used instead of the name from the web interface
            if result.get("test_results"):
                result["test_results"] = list(
                    filter(
                        lambda x: x.get("name") != "Device Name",
                        result.get("test_results"),
                    )
                )

            # Deduplicate test results
            combined = {}
            for t in result.get("test_results", []) + generic_result.get("test_results", []):
                name = t["name"]
                if name not in combined or (combined[name].get("pass") is False and t.get("pass")):
                    combined[name] = t
            result["test_results"] = list(combined.values())
            generic_result.pop("test_results", None)

            for key, value in generic_result.items():
                if isinstance(value, list) and result.get(key):
                    result[key] += value
                elif not result.get(key):
                    result[key] = value

        return result

    except ValueError as err:
        logging.error(err)
        raise HTTPException(status_code=400, detail=f"{err}") from err
    except Exception as err:
        logging.error(err)
        msg = str(err)
        if "invalid response while logging in" in msg.lower() or "login failed" in msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Device login failed while fetching device info. Verify AP credentials/default passwords and that the target is a supported Cambium/Tachyon/Wave AP.",
            ) from err
        raise HTTPException(status_code=500, detail=f"{err}") from err
