#!/usr/bin/python

import requests
import argparse
import os
import pathlib
from time import sleep
from .util import *
import ssl

DEFAULT_UPDATE_FILE = os.getenv("FIRMWARE_PATH") + "/Netonix/wispswitch-1.5.25.bin"

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = os.getenv("SWT_STANDARD_PW")

# Timeout for polling requests when waiting for reboot
DEVICE_WAIT_TIMEOUT = 5


def update_nx_swt(
    ip_address,
    username=DEFAULT_USERNAME,
    password=DEFAULT_PASSWORD,
    firmware_path=DEFAULT_UPDATE_FILE,
    on_log=None,
):
    username = username or DEFAULT_USERNAME
    password = password or DEFAULT_PASSWORD
    firmware_path = firmware_path or DEFAULT_UPDATE_FILE

    session_init = requests.get(f"https://{ip_address}", verify=ssl.CERT_NONE)

    phpsessid = None

    for cookie in session_init.cookies:
        use_callback_or_print(cookie.name + " " + cookie.value, on_log)
        if "PHPSESSID" in cookie.name:
            phpsessid = cookie.value

    cookies = {"PHPSESSID": phpsessid}

    use_callback_or_print(cookies, on_log)

    login_post = requests.post(
        f"https://{ip_address}/index.php",
        verify=ssl.CERT_NONE,
        data={"username": username, "password": password},
        cookies=cookies,
    )
    use_callback_or_print(login_post.status_code, on_log)
    sleep(2)

    with open(firmware_path, "rb") as f:
        data = f.read()
        upload_post = requests.post(
            f"https://{ip_address}/api/v1/uploadfirmware",
            cookies=cookies,
            data=data,
            verify=ssl.CERT_NONE,
        )
        use_callback_or_print(upload_post.status_code, on_log)
        use_callback_or_print(upload_post.content, on_log)
        use_callback_or_print("New firmware file uploaded. Installing...", on_log)

    upgrade_req = requests.get(
        f"https://{ip_address}/api/v1/upgradefirmware",
        verify=ssl.CERT_NONE,
        cookies=cookies,
    )

    use_callback_or_print(upgrade_req.status_code, on_log)

    use_callback_or_print("Firmware installed. Rebooting...", on_log)

    # Wait for reboot
    sleep(5)

    # Continuously send GET requests to determine when device comes online
    while True:
        try:
            get_ping = requests.get(
                f"https://{ip_address}",
                timeout=DEVICE_WAIT_TIMEOUT,
                verify=ssl.CERT_NONE,
            )
            if get_ping.status_code == 200:
                break
            else:
                raise Exception(
                    f"HTTP GET at root returned code {get_ping.status_code}"
                )
        except OSError:
            sleep(1)
            continue

    use_callback_or_print("Firmware updated.", on_log)


def main():
    parser = argparse.ArgumentParser(
        prog="update_nx_swt.py", description="Updates Netonix Switches via HTTP"
    )
    parser.add_argument("ip_address")
    parser.add_argument("-u", "--username")
    parser.add_argument("-p", "--password")
    parser.add_argument("-f", "--update-file", type=pathlib.Path)

    args = parser.parse_args()

    update_nx_swt(
        args.ip_address,
        username=args.username,
        password=args.password,
        firmware_path=args.update_file,
    )


if __name__ == "__main__":
    main()
