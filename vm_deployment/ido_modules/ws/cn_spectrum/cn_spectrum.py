import ssl
import time
from websockets.client import connect
import json
import re
import numpy as np
import traceback
import requests
import logging
import os

DEFAULT_PASSWORDS = [os.getenv("AP_STANDARD_PW"), "admin"]

DEVICES = {
    "EP3K": {
        "range": (4880, 6080),
        "valid_ranges": [
            [5235, 5310],
            [5510, 5695],
            [5190, 5230],
            [5745, 5825],
            [5830, 5870],
        ],
        "step_size": 0.625,
    },
    "4600": {
        "range": (5735, 7125),
        "valid_ranges": [
            # [5235, 5310],
            # [5510, 5695],
            # [5190, 5230],
            # [5745, 5825],
            # [5830, 5870]
        ],
        "step_size": 0.625,
    },
}


class CambiumSpectrumAnalyzer:
    def __init__(self, ip_address, device_type, password=DEFAULT_PASSWORDS[0]):
        self.ip_address = ip_address
        self.device_type = device_type
        self.password = password
        self.secure = False

        self.spectrum = {}

        self.step_size = DEVICES.get(device_type).get("step_size")
        self.frequency_range = DEVICES.get(device_type).get("range")

        self.connection_closed = False

        self.token = None
        self.cookies = None

        self.fill_spectrum()

    def connect(self):
        try:
            # Attempt to use SSL to determine if secure
            requests.get(f"https://{self.ip_address}", verify=False)
            self.secure = True
        except Exception:
            requests.get(f"http://{self.ip_address}")
            self.secure = False
        self._get_stok()
        self._set_spectrum_enabled(True)

    def fill_spectrum(self):
        for i in np.arange(
            self.frequency_range[0],
            self.frequency_range[1] + self.step_size,
            self.step_size,
        ):
            self.spectrum[i] = -1

    def _get_stok(self):
        """Send credentials to AP to acquire login token."""

        # iterate through passwords in DEFAULT_PASSWORDS after trying self.password
        password_index = -1

        while not self.token or not self.cookies:
            try:
                data = {"username": "admin", "password": self.password}

                resp = requests.post(
                    f"{'https' if self.secure else 'http'}://{self.ip_address}/cgi-bin/luci",
                    data=data,
                    verify=False,
                )

                self.token = resp.json().get("stok")
                self.cookies = resp.cookies.get_dict()

                if resp.json().get("msg") == "auth_failed":
                    raise Exception("Invalid credentials.")
                elif resp.json().get("msg") == "max_user_number_reached":
                    raise Exception("Maximum user count reached on AP.")
                elif not self.token:
                    raise Exception(
                        f"Response does not contain a valid token. response: {resp.text}"
                    )

                break
            except Exception as err:
                # Try all passwords in DEFAULT_PASSWORDS
                password_index += 1
                while DEFAULT_PASSWORDS[
                    password_index
                ] == self.password and password_index < len(DEFAULT_PASSWORDS):
                    password_index += 1
                if password_index >= len(DEFAULT_PASSWORDS):
                    raise Exception(f"Failed to acquire AP authentication token. {err}")
                self.password = DEFAULT_PASSWORDS[password_index]

    def _set_spectrum_enabled(self, spectrum_enabled):
        """
        Enables or disables an AP's spectrum analyzer.
            spectrum_enabled: boolean representing desired spectrum analyzer state.
        """
        if not self.token:
            raise Exception("Not logged in.")

        url_root = (
            f"{'https' if self.secure else 'http'}://{self.ip_address}"
            + f"/cgi-bin/luci/;stok={self.token}/admin/"
        )

        data = {
            "changed_elements": json.dumps(
                {"device_props": {"spectralEnable": "1" if spectrum_enabled else "0"}}
            )
        }

        cookies = "; ".join(["=".join(cookie) for cookie in self.cookies.items()])
        cookies += f"; usernameType_{'443' if self.secure else '80'}=admin; stok_{'443' if self.secure else '80'}={self.token}"

        existing_setting_resp = requests.post(
            url_root + "spectral_status",
            data={"stok": self.token, "debug": "true"},
            headers={"cookie": cookies},
            verify=False,
        )

        if existing_setting_resp and existing_setting_resp.json().get("status") == (
            "1" if spectrum_enabled else "0"
        ):
            # If setting is already correct, return
            return

        resp = requests.post(
            url_root + "set_param", data=data, headers={"cookie": cookies}, verify=False
        )

        timeout = time.monotonic() + 5
        spectral_status_resp = None

        while time.monotonic() < timeout and (
            not spectral_status_resp
            or spectral_status_resp.json().get("status")
            != ("1" if spectrum_enabled else "0")
        ):
            # Wait for spectrum status to match `spectrum_enabled`
            spectral_status_resp = requests.post(
                url_root + "spectral_status",
                data={"stok": self.token, "debug": "true"},
                headers={"cookie": cookies},
                verify=False,
            )
            time.sleep(1)

        if spectrum_enabled:
            r = requests.post(
                url_root + "socket_status",
                data={"stok": self.token, "debug": "true"},
                headers={"cookie": cookies},
                verify=False,
            )

            # Wait for config to update
            time.sleep(15)

        if resp.status_code != 200 or resp.json().get("success") != 1:
            raise ConnectionError(f"Parameter set request did not succeed. {resp.text}")
        # elif get_resp.status_code != 200 or get_resp.json().get('success') != '1':
        #    raise Exception(f"Apply get request did not succeed. {get_resp.text}")

    def _logout(self):
        cookies = "; ".join(["=".join(cookie) for cookie in self.cookies.items()])

        cookies += f"; usernameType_{'443' if self.secure else '80'}=admin; stok_{'443' if self.secure else '80'}={self.token}"

        resp = requests.post(
            f'{"https" if self.secure else "http"}://{self.ip_address}/cgi-bin/luci/;stok={self.token}/admin/logout',
            headers={"cookie": cookies},
            verify=False,
        )

        if resp.status_code != 200:
            raise Exception(
                f"Failed to log out. Server returned status code {resp.status_code}."
            )
        elif resp.json().get("msg") == "auth_failed":
            raise Exception("Failed to log out. Authentication failed.")
        else:
            self.cookies = self.token = None

    def close(self):
        if not self.token or not self.cookies:
            return

        try:
            try:
                self._set_spectrum_enabled(False)
            except Exception as err:
                self._logout()
                raise Exception(f"Failed to disable spectrum analyzer.")

            self._logout()

        except Exception as err:
            raise Exception(f"Failed to close connection. {err}") from None

    def frequency_valid(self, frequency):
        for freq_range in DEVICES.get(self.device_type).get("valid_ranges"):
            if frequency >= freq_range[0] and frequency <= freq_range[1]:
                return True
        return False

    def spectrum_is_full(self):
        # Check if data has been received for all frequencies
        for freq in np.arange(
            self.frequency_range[0], self.frequency_range[1], self.step_size
        ):
            if self.spectrum.get(freq) == -1:
                return False
        return True

    async def fetch_spectrum(self, stop_on_full_spectrum=False, new_data_callback=None):
        try:
            if self.secure:
                # Create SSL context without certificate
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            async with connect(
                f"{'wss' if self.secure else 'ws'}://{self.ip_address}/ws",
                ssl=ctx if self.secure else None,
            ) as ws:
                # Init spectrum analyzer
                await ws.send("{'token': '%s', 'init': 1}" % self.token)
                await ws.send(
                    "{'token': '%s','scan':1,'from_freq':%d,'to_freq':%d}"
                    % (self.token, self.frequency_range[0], self.frequency_range[1])
                )
                while not stop_on_full_spectrum or not self.spectrum_is_full():
                    # try:
                    message = json.loads(await ws.recv())

                    if message.get("error"):
                        text = message.get("error_text")
                        await new_data_callback(
                            {
                                "type": "status",
                                "status": "closed",
                                "msg": (
                                    f"Error: {text}"
                                    if text
                                    else "Received error message"
                                ),
                            }
                        )
                        return

                    if not isinstance(message, dict) or message.get("type") != "sa":
                        continue

                    frequency_start = message.get("data", {}).get("frequency")
                    step = message.get("data", {}).get("step")
                    if not self.step_size:
                        self.step_size = step

                    levels = message.get("data", {}).get("levels")

                    # Remove leading / and split by line
                    levels = re.split(r"/+", re.sub("^/*", "", levels))

                    # Store new data (for calling new_data_callback)
                    received_data = {}

                    for i, level in enumerate(levels):
                        # The AP returns a series of 64-character (depending on model) lines separated by "/",
                        # where each character represents a color shown on the spectrum analyzer in the
                        # web UI. An example of a line would be:
                        # /sbVSPMIFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA

                        # Remove "A" (represents whitespace in received spectrum)
                        level_nowhitespace = re.sub(r"[A]", "", level)

                        # Add to dict
                        self.spectrum[frequency_start + step * i] = len(
                            level_nowhitespace
                        )

                        received_data[frequency_start + step * i] = {
                            "level": len(level_nowhitespace),
                            "data": level,
                        }

                    for frequency in received_data.keys():
                        conv = [
                            x
                            for x in self.get_conv_spectrum(
                                # self.get_bandwidth(frequency)
                                40
                            )
                            if x[0] == frequency
                        ]
                        received_data[frequency]["level_conv"] = (
                            conv[0][1] if conv else -1
                        )

                    if callable(new_data_callback):
                        await new_data_callback(
                            {"type": "spectrum", "data": received_data}
                        )

                        # print(json.dumps({"type": "spectrum", "data": received_data}))

                    # except Exception as err:
                    #    logging.error(err)
                    #    #traceback.print_exc()
                    #    # Attempt to re-open connection
                    #    #await ws.send("{'token': '%s', 'init': 1}" % self.token)
                    #    #await ws.send("{'token': '%s','scan':1,'from_freq':%d,'to_freq':%d}" % (
                    #    #    self.token, self.frequency_range[0], self.frequency_range[1]
                    #    #))
                    #    raise err
                self.close()
                if callable(new_data_callback):
                    await new_data_callback(
                        {
                            "type": "status",
                            "status": "closed",
                            "msg": "Frequency scan finished.",
                        }
                    )
        except json.decoder.JSONDecodeError as err:
            logging.debug(err)
        except Exception as err:
            # raise err
            logging.error(err)
            traceback.print_exc()
            if self.cookies and self.token:
                self.close()
            if callable(new_data_callback):
                await new_data_callback(
                    {"type": "status", "status": "closed", "msg": "Connection lost."}
                )
            raise Exception(err)

    def get_conv_spectrum(self, bandwidth):
        """
        Convolve spectrum with boxcar FIR of specified bandwidth.
        Returns values corresponding to the expected interference for each frequency.
        """
        if not self.spectrum or not self.step_size:
            raise Exception("Spectrum has not yet been read.")

        conv_fir = np.array([1 for _ in range(int(bandwidth / self.step_size))])

        spectrum_list = list(self.spectrum.items())

        frequencies = np.array(spectrum_list)[:, 0]
        spectrum = np.array(spectrum_list)[:, 1]

        frequencies = np.append(
            frequencies,
            [
                frequencies[-1] + (i) * self.step_size
                for i in range(1, int(bandwidth / self.step_size))
            ],
        )
        frequencies -= bandwidth / 2

        conv = np.convolve(spectrum, conv_fir)

        return np.vstack([frequencies, conv]).transpose().tolist()

    def get_usage_metric(self, bandwidth):
        """
        Returns a list of values corresponding to how optimal each frequency would be
        for a signal of a given bandwidth.
        """
        usage_metric = []

        for freq, interference in self.get_conv_spectrum(bandwidth):
            usage_metric.append((freq, 64 - interference / (12 * bandwidth / 10)))

        return usage_metric
