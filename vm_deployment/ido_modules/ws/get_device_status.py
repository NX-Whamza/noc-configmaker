#!/usr/local/bin/python3.10

import sys
import json


SOCKET_ENDPOINTS = {
    "/ap-cn": "cambium_ap",
    "/swt-nx": "netonix_switch",
    "/ups-ict": "ict_ups",
    "/rpc-ict": "ict_rpc",
    "/ups-ss": "smartsys_ups",
    "/bh-av": "aviat_backhaul",
}

# MULTI_CONFIG_PATH = "../device_io/"

# try:
#     sys.path.append(MULTI_CONFIG_PATH)
# except Exception as err:
#     raise ImportError(err) from err


def get_device_status(path, on_log=None, **params):
    try:
        if path not in SOCKET_ENDPOINTS:
            raise Exception(f"Invalid websocket endpoint: {path}") from None

        # get path from SOCKET_ENDPOINTS
        path = SOCKET_ENDPOINTS.get(path)
        result = None

        if path == "cambium_ap":
            try:
                from device_io.epmp_config import EPMPConfig
            except Exception as err:
                raise ImportError(err) from err
            finally:
                # params = EPMPConfig.request_params(**params, use_default=True)
                device = EPMPConfig(on_log=on_log, use_default=True, **params)
                if on_log:
                    result = device.pre_check()
                    device.logout()
        elif path == "netonix_switch":
            try:
                from netonix_config import NetonixConfig
            except Exception as err:
                raise ImportError(err) from err
            finally:
                device = NetonixConfig(on_log=on_log, **params)
                if on_log:
                    result = device.pre_check()
        elif path == "ict_ups":
            try:
                from ict_ups_config import ICTUPSConfig
            except Exception as err:
                raise ImportError(err) from err
            finally:
                device = ICTUPSConfig(on_log=on_log, **params)
                if on_log:
                    result = device.pre_check()
        elif path == "ict_rpc":
            try:
                from ict_rpc_config import ICTRPCConfig
            except Exception as err:
                raise ImportError(err) from err
            finally:
                device = ICTRPCConfig(on_log=on_log, **params)
                if on_log:
                    result = device.pre_check()
        elif path == "smartsys_ups":
            try:
                from smart_sys_config import SmartSysConfig
            except Exception as err:
                raise ImportError(err) from err
            finally:
                device = SmartSysConfig(on_log=on_log, **params)
                if on_log:
                    result = device.pre_check()
        elif path == "aviat_backhaul":
            try:
                from wtm4000_config import WTM4000Config
            except Exception as err:
                raise ImportError(err) from err
            finally:
                device = WTM4000Config(on_log=on_log, **params)
                if on_log:
                    result = device.pre_check()

        # Return result as json
        if isinstance(result, list):
            if callable(on_log):
                result = json.dumps({"results": result, "success": True})
                on_log(result)
            else:
                raise Exception("Failed to get device check results.")
    except Exception as err:
        if callable(on_log):
            result = json.dumps({"message": str(err), "success": False})
            print(result)
            on_log(result)
