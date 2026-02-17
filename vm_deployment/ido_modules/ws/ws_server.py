#!/usr/local/bin/python3.11
import asyncio
from urllib.parse import urlparse, parse_qs
import io
import sys
import logging
import websockets
from get_device_status import get_device_status
from update_device import update_device
import re
from get_spectrum_analyzer import get_spectrum_analyzer
import argparse
from os import path
import json

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from device_io.epmp_config import EPMPConfig
from device_io.tachyon_config import TachyonConfig
from device_io.netonix_config import NetonixConfig
from device_io.cnmatrix_config import CNMatrixConfig
from device_io.smart_sys_config import SmartSysConfig
from device_io.ict_rpc_config import ICTRPCConfig
from device_io.ict_ups_config import ICTUPSConfig
from device_io.wtm4000_config import WTM4000Config
from device_io.wave_config import WaveConfig

BIND_ADDRESS = "127.0.0.1"
PORT = 9000
PATH_PREFIX = "/ws"

SOCKET_ENDPOINTS = {
    "/config/ap-cn": "cambium_ap",
    "/config/ap-ty": "tachyon_ap",
    "/config/ap-ub": "wave_ap",
    "/config/swt-nx": "netonix_switch",
    "/config/swt-ty": "tachyon_switch",
    "/config/swt-cn": "cambium_switch",
    "/config/ups-ss": "smart_sys_ups",
    "/config/ups-ict": "ict_ups",
    "/config/rpc-ict": "ict_rpc",
    "/config/bh-aviat": "bh_aviat",
    "/get-status": get_device_status,
    "/update-device": update_device,
    "/spectrum": get_spectrum_analyzer,
}

SEND_LOOP_PERIOD = 0.2
DEBUG_LOGGING = False

class LoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        try:
            websocket = kwargs["extra"]["websocket"]
        except KeyError:
            return msg, kwargs
        xff = websocket.request_headers.get("X-Forwarded-For")
        return f"{websocket.id} {xff} {msg}", kwargs

def handle_endpoint_task(params, path, logstream):
    logger = logging.getLogger(__name__ + f"_{params.get('ip_address')}")
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(
        logging.Formatter(
            f"[{params.get('ip_address')}] %(asctime)s %(levelname)s: %(message)s"
        )
    )
    logger.addHandler(log_handler)

    def on_log(message):
        logstream.write(str(message) + "\n")

    try:
        path = path.replace(PATH_PREFIX, "")
        path_full = path
        path_parsed = None

        while not path_parsed:
            path_parsed = SOCKET_ENDPOINTS.get(path)
            if not path_parsed and not (path := re.sub(r"(.*)/.*?$", r"\1", path)):
                print(f"Invalid websocket endpoint: {path_full}")
                raise ValueError(f"Invalid websocket endpoint: {path_full}") from None

        if callable(path_parsed):
            path_parsed(
                path_full.replace(path, ""),
                on_log=on_log,
                logstream=logstream,
                **params,
            )

        elif path_parsed == "cambium_ap":
            device = EPMPConfig(on_log=on_log, logstream=logstream, **params)
            device.init_and_configure()

        elif path_parsed == "tachyon_ap":
            device = TachyonConfig(on_log=on_log, logstream=logstream, **params)
            device.init_and_configure()

        elif path_parsed == "wave_ap":
            device = WaveConfig(on_log=on_log, logstream=logstream, **params)
            device.init_and_configure()

        elif path_parsed == "netonix_switch":
            dt = params.get("device_type") or ""
            if re.search(r"(WS|NXWS)(12|14)", str(dt), re.I):
                params["device_type"] = "NXWS14"
            elif re.search(r"(WS|NXWS)(24|26)", str(dt), re.I):
                params["device_type"] = "NXWS26"
            device = NetonixConfig(on_log=on_log, logstream=logstream, **NetonixConfig.request_params(**params, use_default=True))
            device.init_and_configure()

        elif path_parsed == "cambium_switch":
            device = CNMatrixConfig(on_log=on_log, logstream=logstream, **params)
            device.init_and_configure()

        elif path_parsed == "tachyon_switch":
            device = TachyonConfig(on_log=on_log, logstream=logstream, **params)
            device.init_and_configure()

        elif path_parsed == "smart_sys_ups":
            params = SmartSysConfig.request_params(**params, use_default=True)
            device = SmartSysConfig(on_log=on_log, logstream=logstream, **params)
            device.init_and_configure()

        elif path_parsed == "ict_rpc":
            params = ICTRPCConfig.request_params(**params, use_default=True)
            device = ICTRPCConfig(on_log=on_log, logstream=logstream, **params)
            device.init_and_configure()

        elif path_parsed == "ict_ups":
            params = ICTUPSConfig.request_params(**params, use_default=True)
            device = ICTUPSConfig(on_log=on_log, logstream=logstream, **params)
            device.init_and_configure()

        elif path_parsed == "bh_aviat":
            device = WTM4000Config(on_log=on_log, logstream=logstream, **params)
            device.init_and_configure()
        else:
            raise ValueError(f"Invalid websocket endpoint: {path_full}") from None

        on_log(json.dumps({"success": True, "message": ""}))
    except Exception as err:
        logger.error(err, exc_info=DEBUG_LOGGING)
        on_log(json.dumps({"success": False, "message": str(err)}))

def get_first_values(input_list):
    for k, v in input_list.items():
        input_list[k] = v[0] if v and isinstance(v, (list, tuple)) else v
    return input_list

async def handle_socket(websocket, path):
    logstream = io.StringIO()
    query = parse_qs(urlparse(path).query)
    print(path)
    if "/spectrum" in path:
        path = path.replace(PATH_PREFIX, "").replace("/spectrum", "")
        task = asyncio.create_task(
            get_spectrum_analyzer(
                websocket, urlparse(path).path, get_first_values(query)
            )
        )
        await task
        await websocket.close()
        return
    task = asyncio.create_task(
        asyncio.to_thread(
            handle_endpoint_task,
            get_first_values(query),
            urlparse(path).path,
            logstream,
        )
    )
    while not task.done():
        await asyncio.sleep(SEND_LOOP_PERIOD)
        await send_output(logstream, websocket)
    await websocket.close()

async def send_output(f, websocket):
    val = f.getvalue()
    if len(val.replace("\n", "")) > 0:
        await websocket.send(val.replace("\0", ""))
    f.truncate(0)

async def run(port):
    async with websockets.serve(
        handle_socket, BIND_ADDRESS, port, logger=logging.getLogger("websockets.server")
    ):
        await asyncio.Future()

def main():
    parser = argparse.ArgumentParser(description="Start Net Launch Tools Server.")
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help="Port on which to listen for incoming connections",
        required=False,
    )
    parser.add_argument(
        "-d",
        "--debug",
        action=argparse.BooleanOptionalAction,
        help="Enable debug logging",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug or DEBUG_LOGGING else logging.INFO
    )
    asyncio.run(run(args.port or PORT))

if __name__ == "__main__":
    main()
