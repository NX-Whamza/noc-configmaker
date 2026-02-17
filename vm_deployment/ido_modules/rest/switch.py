from fastapi import APIRouter, HTTPException
import sys
from os import path
import asyncio
import functools
import concurrent.futures
from .device_info import device_info

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from device_io.netonix_config import NetonixConfig
from device_io.cnmatrix_config import CNMatrixConfig
from device_io.tachyon_config import TachyonConfig

VALID_DEVICE_TYPES = {
    "NXWS12": "NX",
    "NXWS14": "NX",
    "NXWS24": "NX",
    "NXWS26": "NX",
    "CN1012": "CN",
    "TYT100": "TY",
}

app = APIRouter()


@app.get("/api/swt/device_info")
async def get_swt_device_info(
    ip_address: str, device_type: str, run_tests: bool = False
):
    try:
        result = {}
        oem = VALID_DEVICE_TYPES.get(device_type)
        if oem == "NX":
            loop = asyncio.get_running_loop()
            with concurrent.futures.ProcessPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    functools.partial(
                        NetonixConfig.get_device_info,
                        ip_address,
                        device_type,
                        run_tests=run_tests,
                    ),
                )
        elif oem == "CN":
            loop = asyncio.get_running_loop()
            with concurrent.futures.ProcessPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    functools.partial(
                        CNMatrixConfig.get_device_info,
                        ip_address,
                        device_type,
                        run_tests=run_tests,
                    ),
                )
        elif oem == "TY":
            loop = asyncio.get_running_loop()
            with concurrent.futures.ProcessPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    functools.partial(
                        TachyonConfig.get_device_info,
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
