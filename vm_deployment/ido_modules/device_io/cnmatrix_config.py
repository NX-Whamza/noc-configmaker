import os
import json
import logging
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from .util import *

DEBUG = False

CONF_TEMPLATE_PATH = os.getenv("BASE_CONFIG_PATH") + "/Cambium/"

USER = "admin"
PASSWORDS = [os.getenv("CNMATRIX_STANDARD_PW"), "admin"]

DEVICES = {
    "1012": {
        "code": "CN1012",
        "port_count": 12,
        "full_name": "TX1012-P-DC",
        "config": "1012/config.json",
        "bng1_config": "1012/bng1_config.json",
        "bng2_config": "1012/bng2_config.json",
        "dual_uplink_config": "1012/dual_uplink_config.json",
        "firmware_standard": "4.4-r3",
    }
}

# Management VLAN names for BNG 1.0/2.0
INTERFACE_VLAN = {1: "vlan444", 2: "vlan3000"}


class CNMatrixConfig:
    def __init__(self, logstream=None, readonly=False, **params):

        self.ip_address = params["ip_address"]
        self.readonly = readonly

        self.logger = logging.getLogger(__name__ + f"_{self.ip_address}")
        self.logger.setLevel(
            logging.DEBUG if params.get("debug") or DEBUG else logging.INFO
        )

        if logstream:
            log_handler = logging.StreamHandler(logstream)
            log_handler.setFormatter(ConfigLogFormatter())
            log_handler.setLevel(logging.INFO)
            self.logger.addHandler(log_handler)

        self.logger.debug(f"Params: {params}")

        self.device_type = params["device_type"]

        self.username = params.get("username")
        self.password = params.get("password")

        try:
            self.latitude = params["latitude"]
            self.longitude = params["longitude"]
            self.site_name = params["site_name"]
            self.device_number = params.get("device_number", 1)

            self.model = DEVICES[self.device_type]

            self.device_name = (
                f"SWT-{self.model['code']}-{self.model['port_count']}"
                + f"-{self.device_number}.{self.site_name}"
            )

            self.bng_version = int(params.get("bng_version", -1))
            if self.bng_version not in (1, 2):
                self.bng_version = -1

            self.dual_router = params.get("dual_router", False)

        except KeyError as err:
            if not readonly:
                raise KeyError(f"Missing required parameter: {err}") from err

        self.session = None
        self.gambit = None

    def init_session(self, force=False):
        if not force and self.session and self.gambit:
            return

        self.session = requests.Session()

        passwords = PASSWORDS
        if self.password:
            passwords.insert(0, self.password)

        login_req = None

        for password in passwords:
            login_req = self.session.post(
                f"http://{self.ip_address}/iss/redirect.html",
                data={"Login": self.username or USER, "Password": password},
            )

            if login_req.status_code != 200:
                raise ConnectionError("Failed while logging into device.")

            if "ERROR" in login_req.content.decode():
                self.logger.debug(f"Login failed: {login_req.content}")
                continue

            break
        else:
            raise ConnectionError("Login failed.")

        self.logger.info("Logged in.")

        soup = BeautifulSoup(login_req.content.decode(), features="html.parser")
        self.gambit = soup.find("input", attrs={"name": "Gambit"}).attrs.get("value")

    def logout(self):
        if not self.session or not self.gambit:
            return

        self.session.post(
            f"http://{self.ip_address}/wmi/logout", params={"Gambit": self.gambit}
        )

    def get_firmware_version(self):
        self.init_session()

        landing = self.session.get(
            f"http://{self.ip_address}/iss/specific/landing.html",
            params={"Gambit": self.gambit},
        )

        soup = BeautifulSoup(landing.content.decode(), features="html.parser")

        version_elem = soup.find(string="Software Version")

        try:
            return str(list(version_elem.parent.next_siblings)[1].contents[0])
        except Exception:
            raise ConnectionError("Failed to parse landing page contents.")

    def get_address_config(self):
        self.init_session()

        conf = self.session.get(
            f"http://{self.ip_address}/iss/specific/ivr_conf.html",
            params={"Gambit": self.gambit},
        )

        soup = BeautifulSoup(conf.content.decode(), features="html.parser")

        alias_vals = soup.find_all(
            "input", attrs={"name": "ALIAS", "type": "text", "size": "8"}
        )
        address_vals = soup.find_all(
            "input", attrs={"name": "IP_ADDRESS", "type": "text", "size": "15"}
        )
        subnet_vals = soup.find_all(
            "input", attrs={"name": "SUBNET_MASK", "type": "text", "size": "15"}
        )
        bcast_vals = soup.find_all(
            "input", attrs={"name": "BCAST_ADDR", "type": "text", "size": "15"}
        )

        try:
            results = []

            for i, alias in enumerate(alias_vals):
                results.append(
                    {
                        "interface": alias.attrs["value"],
                        "address": address_vals[i].attrs["value"],
                        "subnet_mask": subnet_vals[i].attrs["value"],
                        "broadcast": bcast_vals[i].attrs["value"],
                    }
                )

            return results
        except Exception as err:
            raise ConnectionError(
                "Failed to read device IP address configuration."
            ) from err

    def pre_check(self):
        results = []

        results.append(
            {
                "name": "Firmware version",
                "expected": self.model.get("firmware_standard"),
                "actual": (fw := self.get_firmware_version()),
                "pass": bool(re.match(self.model.get("firmware_standard", ""), fw)),
            }
        )

        ip_conf = self.get_address_config()
        ip_conf = list(filter(lambda x: x["address"] == self.ip_address, ip_conf))
        if not ip_conf:
            raise ConnectionError("Failed to check IP address configuration.")
        ip_conf = ip_conf[0]

        if self.bng_version in INTERFACE_VLAN:

            results.append(
                {
                    "name": "IP VLAN Interface",
                    "expected": INTERFACE_VLAN[self.bng_version],
                    "actual": ip_conf["interface"],
                    "pass": ip_conf["interface"] == INTERFACE_VLAN[self.bng_version],
                    "fail_msg": (
                        "Incorrect management IP address VLAN set for selected BNG version. "
                        + "Configuration will cause the device to become inaccessible."
                    ),
                }
            )

        return results

    def send_configuration(self, path, value):
        # Config files are structured as a json object, where each key represents the path,
        # and each value represents the request body params. If an "add" request fails,
        # it will be retried as an "apply", where an existing parameter is updated with
        # the correct settings. This is needed for parameters such as VLAN settings where the
        # config is a table, where a VLAN can be added, or, if it already exists, can
        # be updated, but cannot be re-added.

        if self.readonly:
            raise Exception("Attempted to configure device in readonly mode.")

        self.init_session()

        now = datetime.now()

        substitutions = {
            "lat": self.latitude,
            "long": self.longitude,
            "site_name": self.site_name[0:15],
            "year": now.strftime("%Y"),
            "month": now.strftime("%m"),
            "day": now.strftime("%d"),
            "hour": now.strftime("%-H"),
            "min": now.strftime("%M"),
            "sec": now.strftime("%S"),
        }
        # Update value dict with substitutions for device
        data = dict(zip(value.keys(), [value[x] % substitutions for x in value.keys()]))

        data["Gambit"] = self.gambit

        self.logger.info(f"Configuring settings at path {path}.")
        self.logger.debug(f"{path}: {data}")
        conf_req = self.session.post(
            f"http://{self.ip_address}{path}",
            params={"Gambit": self.gambit},
            data=data,
        )
        if ">ERROR" in conf_req.content.decode() and value.get("ACTION") in (
            "Add",
            "Create",
        ):
            data["ACTION"].replace("Add", "Apply")
            data["ACTION"].replace("Create", "apply")
            conf_req = self.session.post(f"http://{self.ip_address}{path}", data=data)

        # self.logger.debug(conf_req.content.decode().split("ERROR"))

        if "Current session has been terminated" in conf_req.content.decode():
            raise ConnectionError("Not logged in.")

        if ">ERROR" in (resp := conf_req.content.decode()):
            err = re.findall(r">ERROR: (.*?)<", resp)

            # If the password is changed to the same as the old password, an error will be raised,
            # which should be ignored.
            if "Required differences between the new and old passwords not met" in err:
                return

            self.logger.debug(resp)
            self.logger.debug(conf_req.request.body)
            suffix = (': ' + err[0]) if err else '.'
            raise ValueError(
                f"Configuration failed for path {path} with data {data}{suffix}"
            )

    def upload_configuration_file(self, filename):
        if self.readonly:
            raise Exception("Attempted to configure device in readonly mode.")

        self.init_session()

        with open(filename, "r") as f:
            config = json.load(f)

        for key, value in config.items():
            if isinstance(value, list):
                for item in value:
                    self.send_configuration(key, item)
            elif isinstance(value, dict):
                self.send_configuration(key, value)
            else:
                raise ValueError(f"Invalid value for configuration key {key}")

    def save_configuration(self):
        self.init_session()

        data = {
            "SAVE_OPTION": "2",
            "TRANS_MODE": "1",
            "Save_option": "4",
            "ADDR_TYPE": "1",
            "FILE_NAME": "iss.conf",
            "Save_status": "4",
            "ACTION": "Apply",
            "Gambit": self.gambit,
        }

        self.session.post(f"http://{self.ip_address}/iss/specific/save.html", data=data)
        self.logger.info("\nConfiguration saved.")

    def init_and_configure(self, force_init=False):
        self.init_session(force=force_init)

        precheck = self.pre_check()
        failed = [x for x in precheck if not x.get("pass", True)]
        if failed:
            raise (
                Exception(failed[0]["fail_msg"])
                if "fail_msg" in failed[0]
                else Exception(
                    "Device failed precheck: %(name)s :: expected %(expected)s :: actual %(actual)s"
                    % failed[0]
                )
            )

        if self.model.get("config"):
            self.upload_configuration_file(CONF_TEMPLATE_PATH + self.model["config"])

        if self.bng_version == 1 and self.model.get("bng1_config"):
            self.upload_configuration_file(
                CONF_TEMPLATE_PATH + self.model["bng1_config"]
            )

        if self.bng_version == 2 and self.model.get("bng2_config"):
            self.upload_configuration_file(
                CONF_TEMPLATE_PATH + self.model["bng2_config"]
            )

        if self.dual_router and self.model.get("dual_uplink_config"):
            self.upload_configuration_file(
                CONF_TEMPLATE_PATH + self.model["dual_uplink_config"]
            )

        self.save_configuration()
        self.logout()

    @staticmethod
    def get_device_info(ip_address, device_type, password=None, run_tests=False):
        result = {}

        params = {
            "ip_address": ip_address,
            "device_type": device_type,
        }

        if password:
            params["password"] = password

        d = CNMatrixConfig(**params, readonly=True)
        d.init_session()

        if run_tests:
            result["test_results"] = [
                {"name": x[0], "expected": x[2], "actual": x[1], "pass": x[3]}
                for x in d.pre_check()
            ]

        d.logout()

        return result
