#!/usr/local/bin/python3.10

import sys
import json
import re
import traceback

SOCKET_ENDPOINTS = {
    "/ap-cn": "cambium_ap",
    "/bh-av": "aviat_bh",
}

AVIAT_FIRMWARE_URIS = {
    "4100": {
        "2.11.11": "http://143.55.35.76/updates/wtm4100-2.11.11.18.6069.swpack",
        "6.1.0": "http://143.55.35.76/updates/wtm4100-6.1.0.11.52799.swpack"
    },
    "4200": {
        "2.11.11": "http://143.55.35.76/updates/wtm4100-2.11.11.18.6069.swpack",
        "6.1.0": "http://143.55.35.76/updates/wtm4100-6.1.0.11.52799.swpack"
    }
}


# MULTI_CONFIG_PATH = "../device_io/"

# try:
#     sys.path.append(MULTI_CONFIG_PATH)
# except Exception as err:
#     raise ImportError(err) from err


def update_device(path, on_log=None, logstream=None, **params):
    try:
        if path not in SOCKET_ENDPOINTS:
            raise Exception(f"Invalid websocket endpoint: {path}") from None

        # get path from SOCKET_ENDPOINTS
        path = SOCKET_ENDPOINTS.get(path)
        result = None

        if path == "cambium_ap":
            try:
                from device_io.update_cn_ap import update_cn_ap
            except Exception as err:
                raise ImportError(err) from err

            if not params.get("ip_address") or not re.findall(
                r"(\d{1,3}\.){3}\d{1,3}", params.get("ip_address")
            ):
                raise Exception("Invalid IP address.")

            result = update_cn_ap(
                params.get("ip_address"),
                params.get("device_type"),
                username=params.get("username"),
                password=params.get("password"),
                update_file=params.get("update_version"),
                on_log=on_log,
            )

            # Return result as json
            if isinstance(result, list) and callable(on_log):
                on_log(json.dumps({"results": result, "success": True}))

        elif path == "aviat_bh":
            from device_io.wtm4000_config import WTM4000Config

            w = WTM4000Config(
                ip_address=params.get("ip_address"),
                device_type="AV" + params.get("device_type"),
                password=params.get("password"),
                logstream=logstream,
                readonly=True,
                link_type="dummy",
                xpic=True,
            )
            try:
                if params.get("activate_only") == "true":
                    w.activate_firmware()
                else:
                    uri = params.get("uri") or AVIAT_FIRMWARE_URIS.get(params.get("device_type"), {}).get(params.get("update_version"))
                    w.update_firmware_from_server(
                        uri,
                        activation_time=(
                            params.get("activation_time")
                            if params.get("activation_time") != "null"
                            else None
                        ),
                        activate_now=params.get("activate_now") == "true",
                    )
            finally:
                w.close_session()
        else:
            raise Exception(f"Unknown device path: {path}")

    except Exception as err:
        traceback.print_exc()
        raise err
