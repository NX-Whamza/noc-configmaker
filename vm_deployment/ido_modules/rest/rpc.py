from fastapi import APIRouter, HTTPException
import sys
from os import path
import asyncio
import functools
import concurrent.futures
from .device_info import device_info

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from device_io.ict_rpc_config import ICTRPCConfig

VALID_DEVICE_TYPES = {"ICT200DB": "ICT"}

app = APIRouter()


@app.get("/api/rpc/device_info")
async def get_rpc_device_info(
    ip_address: str, device_type: str, run_tests: bool = False
):
    try:
        result = {}
        oem = VALID_DEVICE_TYPES.get(device_type)
        if oem == "ICT":
            loop = asyncio.get_running_loop()
            with concurrent.futures.ProcessPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    functools.partial(
                        ICTRPCConfig.get_device_info,
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
