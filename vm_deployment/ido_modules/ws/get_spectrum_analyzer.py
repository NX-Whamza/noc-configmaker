import json
import time
import asyncio
import logging
from cn_spectrum import CambiumSpectrumAnalyzer
from threading import Lock

SOCKET_ENDPOINTS = {"/ap-cn": "cambium_ap"}

WS_RX_TIMEOUT = 30


async def get_spectrum_analyzer(websocket, path, params, **kwargs):
    last_receive_time = 0
    last_receive_time_lock = Lock()

    async def send_json_encoded(data):
        last_receive_time_lock.acquire()
        last_receive_time = time.monotonic()
        logging.debug(last_receive_time)
        last_receive_time_lock.release()
        await websocket.send(json.dumps(data) + "\n")

    if path not in SOCKET_ENDPOINTS:
        raise NameError(f"Invalid websocket endpoint: {path}") from None

    # get path from SOCKET_ENDPOINTS
    path = SOCKET_ENDPOINTS.get(path)

    if path == "cambium_ap":
        if not params.get("ip_address") or not params.get("device_type"):
            raise ValueError("Parameters missing.")

        spectrum_analyzer = None
        try:
            spectrum_analyzer = CambiumSpectrumAnalyzer(
                params.get("ip_address"), params.get("device_type")
            )

            await asyncio.to_thread(spectrum_analyzer.connect)

            logging.debug("entering fetch_spectrum")

            task = asyncio.create_task(
                spectrum_analyzer.fetch_spectrum(new_data_callback=send_json_encoded)
            )
            with last_receive_time_lock:
                last_receive_time = time.monotonic()
            while websocket.open and not task.done():
                with last_receive_time_lock:
                    if time.monotonic() - last_receive_time > WS_RX_TIMEOUT:
                        logging.debug(
                            f"Connection timed out at {time.monotonic()} with last receive {last_receive_time}"
                        )
                        break
                await asyncio.sleep(0.1)

            logging.debug("leaving fetch_spectrum")

            if not task.done():
                logging.debug("Websocket closed; task cancelled")
                task.cancel()

            spectrum_analyzer.close()
        except Exception as err:
            await websocket.send(json.dumps({"message": str(err), "success": False}))
            logging.error(err)
            if spectrum_analyzer:
                await asyncio.to_thread(spectrum_analyzer.close)


# def get_spectrum_analyzer(path, on_log=None, **params):
#     def send_json_encoded(data):
#         on_log(json.dumps(data))
#
#     try:
#         if path not in SOCKET_ENDPOINTS:
#             raise NameError(f"Invalid websocket endpoint: {path}") from None
#
#         # get path from SOCKET_ENDPOINTS
#         path = SOCKET_ENDPOINTS.get(path)
#
#         if path == "cambium_ap":
#             if not on_log:
#                 return
#
#             if not params.get("ip_address") or not params.get("device_type"):
#                 raise ValueError("Parameters missing.")
#
#             spectrum_analyzer = None
#             try:
#                 spectrum_analyzer = CambiumSpectrumAnalyzer(
#                     params.get("ip_address"), params.get("device_type")
#                 )
#
#                 spectrum_analyzer.connect()
#                 asyncio.run(
#                     spectrum_analyzer.fetch_spectrum(
#                         new_data_callback=send_json_encoded, stop_on_full_spectrum=True
#                     )
#                 )
#             except Exception as err:
#                 logging.debug(err)
#                 traceback.print_exc()
#                 if spectrum_analyzer:
#                     spectrum_analyzer.close()
#                 on_log(
#                     '{"type": "status", "status": "closed", "msg": "Failed while retrieving spectrum from AP."}'
#                 )
#
#     except Exception as err:
#         if callable(on_log):
#             result = json.dumps({"message": str(err), "success": False})
#             traceback.print_exc()
#             print(result)
#             on_log(result)
