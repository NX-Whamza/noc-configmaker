import json
import re
from datetime import datetime
import os
import time
import logging
import requests
import jsonpath_ng
from .util import timezone_at, parsepath, get_item, ConfigLogFormatter

DEBUG = os.getenv("NETLAUNCH_TOOLS_DEBUG", False)

PRE_CHECK_ATTRIBUTES = {
    "TYN301": [
        {
            "name": "Firmware Version",
            "expected_value": "1.12.0 rev 54573",
            "type": "system",
            "path": "system.version.firmux",
        },
        {
            "name": "Model",
            "expected_value": "TNA-301",
            "type": "system",
            "path": "system.model",
        },
        {
            "name": "SSID",
            "expected_value": None,
            "type": "wireless",
            "path": "wireless.vaps[0].ssid",
        },
        {
            "name": "Wireless MAC",
            "expected_value": None,
            "type": "wireless",
            "path": "wireless.vaps[0].mac",
        },
        # {
        #     "name": "Device Name",
        #     "expected_value": None,
        #     "type": "system",
        #     "path": "system.general.name",
        # },
    ],
    "TYN302": [
        {
            "name": "Firmware Version",
            "expected_value": "1.12.0 rev 54573",
            "type": "system",
            "path": "system.version.firmux",
        },
        {
            "name": "Model",
            "expected_value": "TNA-302",
            "type": "system",
            "path": "system.model",
        },
        {
            "name": "SSID",
            "expected_value": None,
            "type": "wireless",
            "path": "wireless.vaps[0].ssid",
        },
        {
            "name": "Wireless MAC",
            "expected_value": None,
            "type": "wireless",
            "path": "wireless.vaps[0].mac",
        },
        # {
        #     "name": "device_name",
        #     "expected_value": None,
        #     "type": "system",
        #     "path": "system.general.name",
        # },
    ],
    "TYT100": [
        {
            "name": "Firmware Version",
            "expected_value": "1.12.7 rev 54717",
            "type": "system",
            "path": "system.version.firmux",
        },
        {
            "name": "Model",
            "expected_value": "TNS-100",
            "type": "system",
            "path": "system.model",
        },
        # {
        #     "name": "Device Name",
        #     "expected_value": None,
        #     "type": "system",
        #     "path": "system.general.name",
        # },
    ],
}

# Full name, device code, identifier, frequency band
DEVICE_TYPES = [
    ("Tachyon TNA-301", "TYN301", "N301", "60", "AP"),
    ("Tachyon TNA-302", "TYN302", "N302", "60", "SM"),
    ("Tachyon TNS-100", "TYT100", "T100", "0", "SWT"),
]

LOGINS = {
    "AP": [
        f"""{{"username": "admin", "password": "{os.getenv("AP_STANDARD_PW")}"}}""",
        f"""{{"username": "root", "password": "{os.getenv("AP_STANDARD_PW")}"}}""",
        """{"username": "root", "password": "admin"}""",
        f"""{{"username": "admin", "password": "{os.getenv("SM_STANDARD_PW")}"}}""",
        f"""{{"username": "root", "password": "{os.getenv("SM_STANDARD_PW")}"}}""",
    ],
    "SM": [
        f"""{{"username": "admin", "password": "{os.getenv("SM_STANDARD_PW")}"}}""",
        f"""{{"username": "root", "password": "{os.getenv("SM_STANDARD_PW")}"}}""",
        """{"username": "root", "password": "admin"}""",
        f"""{{"username": "admin", "password": "{os.getenv("AP_STANDARD_PW")}"}}""",
        f"""{{"username": "root", "password": "{os.getenv("AP_STANDARD_PW")}"}}""",
    ],
    "SWT": [
        f"""{{"username": "admin", "password": "{os.getenv("SWT_STANDARD_PW")}"}}""",
        f"""{{"username": "root", "password": "{os.getenv("SWT_STANDARD_PW")}"}}""",
        """{"username": "root", "password": "admin"}""",
    ],
}

VALID_CHANNELS = [1, 2, 3, 4, 5, 6]

BASE_CONFIG_FILES = {
    "TYN301": os.getenv("BASE_CONFIG_PATH", "")
    + "/Tachyon/TNA301/standard_config.json",
    "TYN302": os.getenv("BASE_CONFIG_PATH", "")
    + "/Tachyon/TNA302/standard_config.json",
    "TYT100": os.getenv("BASE_CONFIG_PATH", "")
    + "/Tachyon/TNS100/standard_config.json",
}

FIRMWARE_FILES = {
    "TYN301": (
        os.getenv("FIRMWARE_PATH", "")
        + "/Tachyon/TNA301/tna-30x-1.12.0-r54573-20240904-tn-110-prs-squashfs-sysupgrade.bin"
    ),
    "TYN302": (
        os.getenv("FIRMWARE_PATH", "")
        + "/Tachyon/TNA302/tna-30x-1.12.0-r54573-20240904-tn-110-prs-squashfs-sysupgrade.bin"
    ),
    "TYT100": (
        os.getenv("FIRMWARE_PATH", "")
        + "/Tachyon/TNS100/tns-1.12.7-r54717-20250314-tns-100-squashfs-sysupgrade.bin"
    ),
}

ANTENNAS = {"TYN301": [{"name": "TY120"}]}

REBOOT_TIMEOUT = 300


class TachyonConfig:
    def __init__(self, logstream=None, readonly=False, **params):
        self.params = params

        self.readonly = readonly

        self.ip_address = params["ip_address"]
        if not re.match(r"^\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}$", self.ip_address):
            raise ValueError("Invalid value for parameter ip_address.")

        self.password = params.get("password", None)

        self.logger = logging.getLogger(__name__ + f"_{self.ip_address}")
        # self.logger.setLevel(
        #     logging.DEBUG if params.get("debug") or DEBUG else logging.INFO
        # )

        if logstream:
            log_handler = logging.StreamHandler(logstream)
            log_handler.setFormatter(ConfigLogFormatter())
            log_handler.setLevel(logging.INFO)
            self.logger.addHandler(log_handler)

        # Unpack AP type parameters
        [
            self.model_label,
            self.model_code,
            self.model_identifier,
            self.band,
            self.device_category,
        ] = params.get("ap_type", get_item(params.get("device_type"), DEVICE_TYPES))

        # self.is_sm = self.device_category == "SM"

        # validate parameters
        try:
            self.base_config = BASE_CONFIG_FILES[self.model_code]
            self.firmware = FIRMWARE_FILES[self.model_code]

            if self.device_category == "SM":
                self.user_number = params["user_number"]
                self.mac_address = params["mac_address"]
            elif self.device_category == "AP":
                self.channel = int(params["frequency"])
                if self.channel not in VALID_CHANNELS:
                    raise ValueError("Invalid value for parameter frequency.")

                self.azimuth = str(params["azimuth"])
                if not re.match(r"\d{1,3}", self.azimuth):
                    raise ValueError("Invalid value for parameter azimuth.")
                self.azimuth = self.azimuth.rjust(3, "0")

                self.antenna = ANTENNAS[self.model_code][0]["name"]

            if self.device_category != "SM":
                self.site_name = params["site_name"]

            self.device_number = str(params.get("device_number", "1"))
            if not re.match(r"^\d$", self.device_number):
                raise ValueError("Invalid value for parameter device_number.")

            self.latitude = float(params["latitude"])
            if self.latitude > 90 or self.latitude < -90:
                raise ValueError("Latitude out of range.")

            self.longitude = float(params["longitude"])
            if self.longitude > 180 or self.longitude < -180:
                raise ValueError("Longitude out of range.")

        except KeyError as err:
            # If readonly mode is enabled, the above parameters are not necessary, so
            # the device's current state can be read without requiring them.
            if not readonly:
                raise ValueError(f"Missing required parameter: {err}.") from None

        self.session = None

    def init_session(self):
        """Initialize requests session, and login to device."""
        self.session = requests.Session()

        if not self.session:
            raise Exception("Failed to initialize session.")

        logins = LOGINS[self.device_category]
        if self.password:
            logins.insert(
                0,
                f"""{{"username": "root", "password": "{self.password}"}}""",
            )
            logins.insert(
                0,
                f"""{{"username": "admin", "password": "{self.password}"}}""",
            )

        for index, login in enumerate(logins):
            resp = self.session.post(
                f"http://{self.ip_address}/cgi.lua/login", data=login
            )

            body = json.loads(resp.content)
            if not body:
                self.logger.debug(resp.content)
                raise Exception("Failed to read login request response.")

            if body.get("level") == 0 and body.get("auth") is True:
                break

            self.logger.debug(
                f"{index + 1} unsuccessful login attempt{'s' if index != 0 else ''}. {len(logins) - index} remaining."
            )

        if not (body.get("level") == 0 and body.get("auth") is True):
            raise ValueError("Invalid login credentials.")

    def logout(self):
        """Log out of device."""
        if not self.session:
            return

        self.session.delete(f"http://{self.ip_address}/cgi.lua/login")

    def init_and_configure(self):
        if self.readonly:
            raise Exception("Attempted to configure device in readonly mode.")

        self.init_session()

        # Check if device is out of date, and if so, update
        precheck_result = self.pre_check()

        if self.device_category == "SM":
            # Check if MAC address matches
            wireless_mac = [x for x in precheck_result if x[0] == "wireless_mac"]
            if not wireless_mac or (wireless_mac[0][1] != self.mac_address):
                raise ValueError(
                    "Incorrect wireless MAC address provided. Is this the correct device?"
                )

        if not (
            fw_result := [x for x in precheck_result if x[0] == "Firmware Version"]
        ):
            self.logger.warning("Could not determine firmware version.")

        if not fw_result or not fw_result[0][3]:
            # Update firmware if version could not be detected or is incorrect
            self.update_firmware()

        self.update_configuration()

        self.logger.info(
            "\nConfiguration finished.\n"
            + "Device rebooting. Startup may take several minutes."
        )

    def update_configuration(self):
        """Download device's existing config, modify according to changes in base config,
        then re-upload."""

        if self.readonly:
            raise Exception("Attempted to update config in readonly mode.")

        config = self.get_running_config()

        base_config = self.get_standard_config()

        for change in base_config:
            if isinstance(change["value"], bool):
                value = "true" if change["value"] else "false"
            else:
                value = change["value"]

            self.logger.info("Setting parameter %s to %s." % (change["path"], value))

            expression = jsonpath_ng.parse(change["path"])

            expression.update(config, change["value"])

        # Set parameters that vary according to each individual device

        if self.device_category == "AP":
            # Wireless channel
            self.logger.info(
                "Setting parameter wireless.radios.wlan0.channel.number to %s."
                % self.channel,
            )
            jsonpath_ng.parse("wireless.radios.wlan0.channel.number").update(
                config, self.channel
            )

            # SSID
            self.logger.info(
                "Setting parameter wireless.radios.wlan0.vaps[0].ssid to %s."
                % f"{self.azimuth}-{self.device_number}.{self.site_name}",
            )
            jsonpath_ng.parse("wireless.radios.wlan0.vaps[0].ssid").update(
                config, f"{self.azimuth}-{self.device_number}.{self.site_name}"
            )

            # Device name
            self.logger.info(
                "Setting parameter system.name to %s."
                % f"AP-{self.model_code}-{self.band}-{self.antenna}-"
                + f"{self.azimuth}-{self.device_number}",
            )
            jsonpath_ng.parse("system.name").update(
                config,
                f"AP-{self.model_code}-{self.band}-{self.antenna}-"
                + f"{self.azimuth}-{self.device_number}",
            )
            self.logger.info(
                "Setting parameter system.hostname to %s."
                % f"AP-{self.model_code}-{self.band}-{self.antenna}-"
                + f"{self.azimuth}-{self.device_number}.{self.site_name}",
            )
            jsonpath_ng.parse("system.hostname").update(
                config,
                f"AP-{self.model_code}-{self.band}-{self.antenna}-"
                + f"{self.azimuth}-{self.device_number}.{self.site_name}",
            )

        elif self.device_category == "SM":
            # Hostname
            self.logger.info(
                "Setting parameter system.name to %s." % (f"NX-{self.user_number}"),
            )
            jsonpath_ng.parse("system.name").update(config, f"NX-{self.user_number}")

            self.logger.info(
                "Setting parameter system.hostname to %s." % (f"NX-{self.user_number}"),
            )
            jsonpath_ng.parse("system.hostname").update(
                config, f"NX-{self.user_number}"
            )

        elif self.device_category == "SWT":
            self.logger.info(
                "Setting parameter system.name to %s."
                % f"SWT-{self.model_code}-6-{self.device_number}.{self.site_name}",
            )
            jsonpath_ng.parse("system.name").update(
                config, f"SWT-{self.model_code}-6-{self.device_number}.{self.site_name}"
            )
            self.logger.info(
                "Setting parameter system.hostname to %s."
                % f"SWT-{self.model_code}-6-{self.device_number}.{self.site_name}",
            )
            jsonpath_ng.parse("system.hostname").update(
                config,
                f"SWT-{self.model_code}-6-{self.device_number}.{self.site_name}",
            )

        self.logger.info(
            "Setting parameter system.time.time to %s."
            % datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        jsonpath_ng.parse("system.time.time").update(
            config, datetime.now().strftime("%Y-%m-%d %H:%M")
        )

        # Location
        self.logger.info(
            "Setting parameter system.location to %s."
            % f"{self.latitude:.5f}, {self.longitude:.5f}",
        )
        jsonpath_ng.parse("system.location").update(
            config,
            f"{self.latitude:.5f}, {self.longitude:.5f}",
        )

        self.upload_configuration(config)

    def get_running_config(self, paths=False):
        """Get existing configuration file from device."""
        if not self.session:
            self.init_session()

        resp = self.session.get(f"http://{self.ip_address}/cgi.lua/config")

        config = json.loads(resp.content)

        if paths:
            return parsepath(config, include_empty_vals=True)

        return config

    def get_standard_config(self):
        try:
            with open(self.base_config, "r") as f:
                config = json.load(f)
        except Exception as err:
            raise SystemError(f"Failed to read base config file. {err}") from err

        return config

    def upload_configuration(self, config):
        """Upload a configuration file to the device, with reboot."""
        if self.readonly:
            raise Exception("Attempted to upload config in readonly mode.")

        if not self.session:
            self.init_session()

        self.logger.debug(config)

        resp = self.session.post(
            f"http://{self.ip_address}/cgi.lua/config",
            data=json.dumps({"data": config, "rebootRequired": True}),
            timeout=REBOOT_TIMEOUT
        )

        if resp.status_code != 200:
            raise ConnectionError(
                f"Failed to upload config. Status code {resp.status_code}"
            )

    def timezone(self):
        """Get time zone and format for tachyon config."""

        tz = timezone_at(self.latitude, self.longitude)

        # Tachyon configs use the format "UTC<offset>", e.g. "UTC-6"
        if tz["offset_hours"] == 0:
            utc_offset = "UTC"
        elif tz["offset_hours"] > 0:
            utc_offset = f"UTC+{tz['offset_hours']}"
        else:
            utc_offset = f"UTC{tz['offset_hours']}"

        return {"name": tz["name"], "utc_offset": utc_offset}

    def pre_check(self):
        result = []

        if not self.session:
            self.init_session()

        for attribute in PRE_CHECK_ATTRIBUTES[self.model_code]:
            resp = self.session.get(
                f"http://{self.ip_address}/cgi.lua/status?type={attribute['type']}"
            )
            if not resp.content or resp.content.decode("utf-8") == "{}":
                raise ValueError("Attribute type not found.")

            try:
                expression = jsonpath_ng.parse(attribute["path"])

                value = [m.value for m in expression.find(json.loads(resp.content))]

                if not value:
                    raise NameError("Attribute not found.")

                value = value[0]
            except Exception as err:
                raise ValueError(f"Could not parse value. {err}") from err

            result.append([
                attribute["name"],
                value,
                attribute["expected_value"],
                (
                    None
                    if not attribute["expected_value"]
                    else value in attribute["expected_value"]
                ),
            ])

        return result

    def update_firmware(self):
        if self.readonly:
            raise Exception("Attempted to update device firmware in readonly mode.")

        self.logger.info("Updating firmware...")

        if not self.session:
            self.init_session()

        with open(self.firmware, "rb") as f:
            upload = self.session.put(
                f"http://{self.ip_address}/cgi.lua/update", files={"fw": f}
            )

        if upload.status_code != 200:
            raise ConnectionError(
                f"Failed to upload firmware. Status code: {upload.status_code}"
            )

        self.logger.info("Firmware uploaded. Installing...")

        install = self.session.post(
            f"http://{self.ip_address}/cgi.lua/update",
            data="""{"reset":false,"force":false}""",
        )

        if install.status_code != 200:
            raise ConnectionError(
                f"Failed to install firmware. Status code: {install.status_code}"
            )

        self.wait_for_reboot()

        self.logger.info("Firmware updated.")

    def wait_for_reboot(self):
        start_time = time.monotonic()

        # Repeatedly attempt login until timeout
        while time.monotonic() < start_time + REBOOT_TIMEOUT:
            try:
                self.init_session()
                return

            # If an Exception is raised, assume connection error, unless it is a ValueError
            except ValueError:
                raise
            except Exception:
                continue

        raise TimeoutError("Timed out while waiting for reboot.")

    def get_device_params(self):
        if not self.session:
            self.init_session()

        resp = self.session.get(
            f"http://{self.ip_address}/cgi.lua/status?type=network,zones,interfaces,ethernet,dhcp_status,system"
        )
        if not resp.content or resp.content.decode("utf-8") == "{}":
            raise ValueError("Failed to retrieve status.")

        return json.loads(resp.content)

    @staticmethod
    def get_device_info(ip_address, device_type, password=None, run_tests=False):
        result = {}

        params = {
            "ip_address": ip_address,
            "device_type": device_type,
        }

        d = None

        [
            model_label,
            model_code,
            model_identifier,
            band,
            device_category,
        ] = get_item(device_type, DEVICE_TYPES)

        if password:
            params["password"] = password

        try:
            d = TachyonConfig(**params, readonly=True)
            d.init_session()
            params = d.get_device_params()
            # Convert JSON paths to lines of text
            result["standard_config"] = (
                "\n".join(
                    sorted([
                        f"{line['path']}: {line['value']}"
                        for line in d.get_standard_config()
                    ])
                )
                .replace("False", "false")
                .replace("True", "true")
            ) + "\n"
            result["running_config"] = (
                "\n".join(
                    sorted([
                        f"{line['path']}: {line['value']}"
                        for line in d.get_running_config(paths=True)
                    ])
                )
                .replace("False", "false")
                .replace("True", "true")
            ) + "\n"
            if run_tests:
                result["test_results"] = [
                    {"name": x[0], "expected": x[2], "actual": x[1], "pass": x[3]}
                    for x in d.pre_check()
                ]

            d.logout()

            lat_long = re.match(
                r"^(\d+\.\d+),\s*(\d+\.\d+)", params["system"]["general"]["location"]
            )

            if lat_long:
                result["latitude"] = lat_long.group(1)
                result["longitude"] = lat_long.group(2)

            if device_category == "AP":
                result["wireless_mac"] = (
                    params.get("interfaces", {}).get("wlan0", {}).get("mac_address")
                )
                result["sm_count"] = list(
                    filter(
                        lambda x: x[0] != "totals",
                        params.get("prs_events", {}).get("peers", {}).items(),
                    )
                )
            if device_category == "SM":
                result["wireless_mac"] = (
                    params.get("interfaces", {}).get("wlan0", {}).get("mac_address")
                )

            result["success"] = True

        except Exception as err:
            try:
                if d:
                    d.logout()
            except Exception:
                pass

            print(err)

            result["success"] = False
            result["message"] = str(err)

        return result
