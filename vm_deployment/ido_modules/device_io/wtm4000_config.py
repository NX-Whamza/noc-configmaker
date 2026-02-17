#!/usr/bin/python3
import pathlib
import re
import sys
import time
from pathlib import Path
import os
import logging
import asyncio
from .util import *
import paramiko
import websockets
import websockets.sync.client
import requests
import pandas as pd

CONF_TEMPLATE_PATH = os.path.join(os.getenv("BASE_CONFIG_PATH", "/opt/base_configs"), "Aviat")
CONF_TEMPLATE_FOLDERS = {
    "2.11": "",
    "6.1":  "Aviat-6.1.0",
}

FIRMWARE_PATH_BASE = os.getenv("FIRMWARE_PATH") + "/Aviat"
FW_UPLOAD_MAX_UPTIME = 250 * 86400

LINK_DATA_URL = "https://ltetool.nxlink.com/static/mwlinks-v2.csv"
LINK_DATA_CACHE_DIR = os.getenv("NETLAUNCH_TOOLS_CACHE_DIR", "/var/cache/netlaunch-tools/")
LINK_DATA_CACHE_FILE = os.path.join(LINK_DATA_CACHE_DIR, "links.csv")
LINK_DATA_CACHE_TTL = 86400

PRE_CHECK_ATTRIBUTES = []

RADIO_MODELS = [
    ("Aviat WTM4100", "AV4100", "WTM4100"),
    ("Aviat WTM4200", "AV4200", "WTM4200"),
]

DEFAULT_FIRMWARE_URI = "http://143.55.35.76/updates/wtm4100-2.11.11.18.6069.swpack"
FINAL_FIRMWARE_URI = "http://143.55.35.76/updates/wtm4100-6.1.0.11.52799.swpack"
BASELINE_VERSION = "2.11.11"
FINAL_VERSION = "6.1.0"

RADIO_FIRMWARE = {
    "AV4100": {
        "file": FIRMWARE_PATH_BASE + "/4100/wtm4100-2.11.11.18.6069.swpack",
        "size": 111877365,
        "filename": "wtm4100-2.11.11.18.6069.swpack",
    },
    "AV4200": {
        "file": FIRMWARE_PATH_BASE + "/4100/wtm4100-2.11.11.18.6069.swpack",
        "size": 111877365,
        "filename": "wtm4100-2.11.11.18.6069.swpack",
    },
}

RADIO_CONFIGS = {
    "AV4100": {
        "xpic": [
            {"file": "", "keyword": "dummy", "licenses": []},
            {
                "file": "4100/4_0_vert_master.config",
                "keyword": "4_0_V",
                "licenses": [
                    "WZL-CE1",
                    "WZL-ENTERPRISE5",
                    "WZF-MLHC",
                    "WZF-XPIC",
                    "WZF-L1LA",
                ],
            },
            {
                "file": "4100/4_0_horiz_slave.config",
                "keyword": "4_0_H",
                "licenses": [
                    "WZL-CE1",
                    "WZL-ENTERPRISE5",
                    "WZF-MLHC",
                    "WZF-XPIC",
                    "WZF-L1LA",
                ],
            },
        ],
        "non-xpic": [
            {
                "file": "4100/4_0_vert_master.config",
                "keyword": "4_0_V",
                "licenses": [
                    "WZL-CE1",
                    "WZL-ENTERPRISE5",
                    "WZF-MLHC",
                    "WZF-XPIC",
                    "WZF-L1LA",
                ],
            },
            {
                "file": "4100/4_0_horiz_slave.config",
                "keyword": "4_0_H",
                "licenses": [
                    "WZL-CE1",
                    "WZL-ENTERPRISE5",
                    "WZF-MLHC",
                    "WZF-XPIC",
                    "WZF-L1LA",
                ],
            },
            {
                "file": "4100/2_0.config",
                "keyword": "2_0",
                "licenses": [
                    "WZL-CE1",
                    "WZL-ENTERPRISE5",
                    "WZF-MLHC",
                ],
            },
        ],
    },
    "AV4200": {
        "xpic": [
            {"file": "", "keyword": "dummy", "licenses": []},
            {
                "file": "4200/2_0_xpic.config",
                "keyword": "2_0",
                "licenses": ["WZL-CE1", "WZL-ENTERPRISE2", "WZF-MLHC"],
            },
        ],
        "non-xpic": [
            {
                "file": "4200/2_0.config",
                "keyword": "2_0",
                "licenses": ["WZL-CE1", "WZL-ENTERPRISE2", "WZF-MLHC"],
            }
        ],
    },
}

SFP_ALLOWED_PREFIXES = ["SFP-10G-LR-X-"]

BANDWIDTHS = ["25 MHz", "30 MHz", "40 MHz", "50 MHz", "60 MHz", "75 MHz", "80 MHz"]

MODULATION_MIN = [
    "quarter-qpsk",
    "half-qpsk",
    "qpsk",
    "qam-16",
    "qam-32",
    "qam-64",
    "qam-128",
    "qam-256",
    "qam-512",
    "qam-1024",
    "qam-2048",
    "qam-4096",
]

MODULATION_MAX = [
    "quarter-qpsk",
    "half-qpsk",
    "qpsk",
    "qam-16",
    "qam-32",
    "qam-64",
    "qam-128",
    "qam-256",
    "qam-512",
    "qam-1024",
    "qam-2048",
    "qam-4096",
]

PASSWORDS = [os.getenv("BH_STANDARD_PW"), "admin"]

MIN_POWER_RANGE = [11.5, 25.5]
MAX_POWER_RANGE = [11.5, 31.0]
AV4200_WPX_TX_RANGE = (10918.5, 11196.5)
AV4200_WPX_RX_RANGE = (11428.5, 11701.5)
RSL_RANGE = (-3, 3)

SITE_NAME_REGEXES = [
    r"BH-AV\S{4}-\d+-(\S*)\.(\S*)",
    r"(\w*)\.(\w*)$",
    r"BH-.*?([A-Z]{2}-\S*)\.(\S*)",
]

HELP_MESSAGE = (
    "Usage: %s [-b bandwidth] [-c config] [-d device_type] [-i ip_address]\n\
                     [-M max_modulation] [-m min_modulation] [-n site_name] [-P max_power]\n\
                     [-p min_power] [-R remote_name] [-r rx_frequency] [-s ssh_password]\n\
                     [-t tx_frequency]\n\
                \n\
            Available options:\n\
                -b,--bandwidth      Bandwidth of backhaul link, in MHz\n\
                -i,--ip-address     IP address of backhaul to configure\n\
                -n,--site-name      Name of site on local side of link, in format AA-BBBBBB-CC-##\n\
                -R,--remote-site    Name of site on remote side of link, in format AA-BBBBBB-CC-##\n\
                -t,--tx-frequency   Frequency at which radio will transmit\n\
                -r,--rx-frequency   Frequency at which remote backhaul transmits\n\
                -M,--modulation-max Maximum modulation scheme\n\
                -m,--modulation-min Minimum modulation scheme\n\
                -P,--power-max      Maximum transmit power, in dBm\n\
                -p,--power-min      Minimum transmit power, in dBm\n\
                -h,--help           Show this help message\n\
                -s,--ssh-password"
    % (__file__.split("/")[-1])
)

DEBUG = bool(os.getenv("NETLAUNCH_TOOLS_DEBUG", False))
DISABLE_PRECHECK = False
SSH_SEND_TIMEOUT = 30
LOGIN_TIMEOUT = 30
UPTIME_CHECK_TIMEOUT = 5

class WTM4000Config:
    def __init__(self, logstream=None, readonly=False, **params):
        self.readonly = readonly
        self.ip_address = params["ip_address"]
        self.device_type = params["device_type"]
        self.radio_type = get_item(params["device_type"], RADIO_MODELS)
        self.logger = logging.getLogger(__name__ + f"_{self.ip_address}")
        self.logger.setLevel(
            logging.DEBUG if params.get("debug") or DEBUG else logging.INFO
        )
        if logstream:
            log_handler = logging.StreamHandler(logstream)
            log_handler.setFormatter(ConfigLogFormatter())
            log_handler.setLevel(logging.INFO)
            self.logger.addHandler(log_handler)
        self.username = "admin"
        self.ssh_password = params.get("password")
        try:
            self.link_type = params["link_type"]
            self.site_name = params.get("local_site_name")
            self.remote_site_name = params.get("remote_site_name")
            self.tx_frequency_v = float(
                re.sub(r"[A-Za-z ]", "", str(params["tx_frequency_v"]))
            )
            self.rx_frequency_v = float(
                re.sub(r"[A-Za-z ]", "", str(params["rx_frequency_v"]))
            )
            self.tx_frequency_h = float(
                re.sub(r"[A-Za-z ]", "", str(params["tx_frequency_h"]))
            )
            self.rx_frequency_h = float(
                re.sub(r"[A-Za-z ]", "", str(params["rx_frequency_h"]))
            )
            self.bandwidth = params["bandwidth"]
            self.modulation_min = params.get("modulation_min")
            self.modulation_max = params.get("modulation_max")
            self.power_min = "%.01f" % float(params["power_min"])
            self.power_max = "%.01f" % float(params["power_max"])
            self.rsl_max = params.get("rsl_max")
            self.latitude = params.get("latitude")
            self.longitude = params.get("longitude")
            self.device_name = "BH-%s-%d-%s.%s" % (
                self.radio_type[1],
                int(round(float(self.tx_frequency_v) / 1000)),
                self.remote_site_name,
                self.site_name,
            )
        except KeyError as err:
            if not readonly:
                raise ValueError("Invalid value: %s" % err) from err
        try:
            self.sesh = None
            self.req_session = None
            self.use_xpic = bool(params.get("xpic")) or (
                not readonly and self.tx_frequency_v == self.tx_frequency_h
            )
            self.radio_config = None
            for config in RADIO_CONFIGS[self.device_type][
                "xpic" if self.use_xpic else "non-xpic"
            ]:
                if config["keyword"] == self.link_type:
                    self.radio_config = config
                    break
            if not self.radio_config:
                raise ValueError(f"Invalid config for device type: {self.link_type}")
        except KeyError as err:
            raise ValueError("Missing required value: %s" % err) from err
        self.ssh = None
        self.ssh_channel = None
        self.template_folder_key = "2.11"

    def _set_template_folder_from_fw(self, version_str):
        v = self.version_tuple(version_str)
        if v >= self.version_tuple(FINAL_VERSION):
            self.template_folder_key = "6.1"
        else:
            self.template_folder_key = "2.11"

    def _detect_4200_variant(self):
        if self.device_type != "AV4200":
            return None
        fw = self.get_firmware_version()
        use_61 = self.version_tuple(fw) >= self.version_tuple("6.1.0")
        data = ""
        if use_61:
            try:
                data = self.send_ssh_command("show hardware System/Root1")
                m = re.search(r"\bmodel name\s+.*?-([WD]PX)\b", data, flags=re.I)
                if m:
                    return m.group(1).upper()
            except Exception:
                pass
        else:
            try:
                data = self.send_ssh_command("show manufacture-details Terminal1")
                m = re.search(r"\bpart-number\s+.*?-([WD]PX)\b", data, flags=re.I)
                if m:
                    return m.group(1).upper()
            except Exception:
                pass
        blobs = []
        for cmd in ("show hardware", "show manufacture-details", "show version"):
            try:
                blobs.append(self.send_ssh_command(cmd))
            except Exception:
                continue
        data = "\n".join(blobs)
        m = re.search(r"\b(WPX|DPX)\b", data, flags=re.I)
        if m:
            return m.group(1).upper()
        m = re.search(r"WTM4200[- ]?(WPX|DPX)", data, flags=re.I)
        if m:
            return m.group(1).upper()
        return None

    def _enforce_frequency_limits_4200(self):
        if self.device_type != "AV4200":
            return
        variant = self._detect_4200_variant() or "DPX"
        self.logger.info(f"WTM4200 variant: {variant}")
        if variant != "WPX":
            return
        def in_range(v, rng):
            return rng[0] <= float(v) <= rng[1]
        tx_vals = [self.tx_frequency_v, self.tx_frequency_h]
        rx_vals = [self.rx_frequency_v, self.rx_frequency_h]
        bad_tx = [str(x) for x in tx_vals if not in_range(x, AV4200_WPX_TX_RANGE)]
        bad_rx = [str(x) for x in rx_vals if not in_range(x, AV4200_WPX_RX_RANGE)]
        if bad_tx or bad_rx:
            tx_rng = f"{AV4200_WPX_TX_RANGE[0]}–{AV4200_WPX_TX_RANGE[1]} MHz"
            rx_rng = f"{AV4200_WPX_RX_RANGE[0]}–{AV4200_WPX_RX_RANGE[1]} MHz"
            raise ValueError(
                "WTM4200 WPX frequency limits violated. "
                + (f"TX out of range: {', '.join(bad_tx)}. " if bad_tx else "")
                + (f"RX out of range: {', '.join(bad_rx)}. " if bad_rx else "")
                + f"Required ranges: TX {tx_rng}, RX {rx_rng}."
            )

    def init_ssh(self, username=None, password=None, force=False, suppress_info_log=False):
        if (
            not force
            and isinstance(self.ssh_channel, paramiko.Channel)
            and self.ssh_channel.active == 1
        ):
            return
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        passwords = []
        if password:
            passwords.append(password)
        if self.ssh_password:
            passwords.append(self.ssh_password)
        passwords += PASSWORDS
        ssh_transport = None
        for pw in passwords:
            try:
                self.ssh.connect(
                    self.ip_address,
                    username=username or self.username,
                    password=pw,
                    timeout=LOGIN_TIMEOUT,
                )
                ssh_transport = self.ssh.get_transport()
                break
            except paramiko.AuthenticationException:
                continue
        if not ssh_transport:
            raise ConnectionError("Failed to log into device. Is the password correct?")
        self.ssh_channel = ssh_transport.open_session()
        self.ssh_channel.get_pty()
        self.ssh_channel.invoke_shell()
        time.sleep(2)
        ctr = 0
        while "#" not in self.ssh_channel.recv(1024).decode():
            if ctr > 75:
                raise ConnectionError("Failed to open SSH session.")
            time.sleep(0.2)
            ctr += 1
        self.send_ssh_command("set paginate false")
        self.send_ssh_command("set complete-on-space false")
        if not suppress_info_log:
            self.logger.info("Connected to device.")

    def close_session(self):
        if self.ssh:
            self.ssh.close()

    def send_ssh_command(self, command, info_log=False):
        try:
            if not self.ssh or not self.ssh_channel:
                self.init_ssh()
        except AttributeError:
            self.init_ssh()
        if not self.ssh or not self.ssh_channel:
            self.init_ssh()
        if info_log:
            self.logger.info(f"Sending command: {command}")
        else:
            self.logger.debug(f"Sending command: {command}")
        try:
            output = ""
            command = re.sub(r"\s*$", r"", command)
            while self.ssh_channel.recv_ready():
                time.sleep(0.1)
                self.ssh_channel.recv(4096)
            self.ssh_channel.sendall((command + "\n").encode())
            send_time = time.perf_counter()
            while (
                time.perf_counter() < send_time + SSH_SEND_TIMEOUT
                and not len(re.findall(r"^\S*# ", output, flags=re.M) or []) > 0
                and not len(
                    re.findall(r"^Value for \'\S*\' \[\S*\]:", output, flags=re.M) or []
                )
                > 0
            ):
                if self.ssh_channel.recv_ready():
                    output += (
                        self.ssh_channel.recv(4096)
                        .decode("ascii")
                        .replace("\\n", "\n")
                        .replace("\\t", "\t")
                        .replace("\r", "")
                    )
                    if "The value must be one of:" in output:
                        raise ValueError(
                            f"Failed to configure parameter: {command}\n"
                            + f"The value must be one of: {output.split('The value must be one of:')[1]}"
                        )
                time.sleep(0.1)
            self.logger.debug(output)
            return output
        except paramiko.SSHException as err:
            raise Exception("Error while sending ssh command '%s': \n%s" % (command, err))

    def _template_base(self):
        folder = CONF_TEMPLATE_FOLDERS[self.template_folder_key]
        base = pathlib.Path(CONF_TEMPLATE_PATH)
        return base / folder if folder else base

    def get_standard_config(self, json_conf=False, paths=False):
        config_path = pathlib.PurePath(self._template_base(), self.radio_config["file"])
        config = read_file(config_path)
        if not json_conf:
            return config
        config = self.parse_config(config)
        if paths:
            return parsepath(config, delim=" ")
        return json.dumps(config, sort_keys=True, indent=4)

    @staticmethod
    def parse_config_part(lines, index):
        def numspaces(s):
            return len(s) - len(s.lstrip(" "))
        if index < len(lines) - 1:
            if numspaces(lines[index + 1]) > numspaces(lines[index]):
                key = re.sub(r"^\s*(.*\w)\s*\n?", r"\g<1>", lines[index])
                value = {}
                current_index = index
                while current_index < len(lines):
                    if (
                        numspaces(lines[current_index + 1]) <= numspaces(lines[index])
                        and "exit" not in lines[current_index + 1]
                    ):
                        break
                    nested_line = WTM4000Config.parse_config_part(lines, current_index + 1)
                    if not nested_line:
                        current_index += 1
                        break
                    value[nested_line[0]] = (
                        nested_line[1] if len(nested_line) > 1 else None
                    )
                    current_index = nested_line[2]
                return (key, value, current_index)
        if "exit" in lines[index]:
            return
        match = re.match(r"\s*(.*?\w)\s+\[ (\w.*\w) \]", lines[index])
        if match:
            return (match.group(1), match.group(2).split(" "), index)
        match = re.match(r"^\s*(.+?\w)(?:\s+\"(.*)\"|\s+(\S+))?$", lines[index])
        if match:
            if match.group(1) == "no" and match.group(3):
                return (match.group(3), False, index)
            return (match.group(1), match.group(2) or match.group(3) or True, index)

    @staticmethod
    def parse_config(config):
        index = 0
        result = {}
        lines = config.split("\n")
        while index < len(lines):
            parsed_line = WTM4000Config.parse_config_part(lines, index)
            if not parsed_line:
                index += 1
                continue
            index = parsed_line[2] + 1
            result[parsed_line[0]] = parsed_line[1]
        return result

    def get_running_config(self, json_conf=False, paths=False):
        config = self.send_ssh_command("show running-config")
        config = re.search(r"\A.*?show running-config\n(.*)\n.*?#.*?\Z", config, re.M | re.S)
        if not config:
            raise Exception("Failed to get running config.")
        if not json_conf:
            return config.group(1)
        config_dict = self.parse_config(config.group(1))
        if paths:
            return parsepath(config_dict, delim=" ")
        return json.dumps(config_dict, sort_keys=True, indent=4)

    def get_license_bundles(self):
        output = self.send_ssh_command("show licensing bundles")
        bundles = []
        for line in output.splitlines():
            line = line.strip()
            if not line or line.upper() in ("BUNDLE", "ENTITY", "NAME") or re.match(r"^-{3,}$", line):
                continue
            m = re.match(r"^\S+\s+([A-Za-z0-9-]+)\s*$", line)
            if m:
                name = m.group(1)
                if name and name.lower() != "trial":
                    bundles.append(name)
            else:
                if re.match(r"^[A-Za-z0-9-]+$", line) and line.lower() != "trial":
                    bundles.append(line)
        return bundles

    def get_licenses(self):
        output = self.send_ssh_command("show licensing")
        licenses_parsed = {}
        licenses = re.findall(r"licensing \S* .*\n(?:^ .*\n)*", output, flags=re.M)
        for license in licenses:
            if "feature" not in license:
                continue
            if "licensing licenses" in license:
                if (
                    not licenses_parsed.get(
                        (m := re.search(r"^ feature *(\S*)\s*$", license, flags=re.M))
                        and m.group(1)
                    )
                    or not licenses_parsed.get(
                        (m := re.search(r"^ feature *(\S*)$", license, flags=re.M))
                        and m.group(1),
                        {},
                    ).get("is_trial")
                    == "false"
                ):
                    licenses_parsed[
                        (m := re.search(r"^ feature *(\S*)\s*$", license, flags=re.M))
                        and m.group(1)
                    ] = {
                        **(
                            licenses_parsed.get(
                                (
                                    m := re.search(
                                        r"^ feature *(\S*)\s*$", license, flags=re.M
                                    )
                                )
                                and m.group(1)
                            )
                            or {}
                        ),
                        "id": (
                            m := re.match(r"licensing licenses ([0-9A-F]{16})", license)
                        )
                        and m.group(1),
                        "version": (
                            (m := re.search(r"version *(\S*)", license)) and m.group(1)
                            if "version" in license
                            else None
                        ),
                        "bundle": (
                            (m := re.search(r"bundle *(\S*)", license)) and m.group(1)
                            if "bundle" in license
                            else None
                        ),
                        "instances": (
                            (m := re.search(r"instances *(\S*)", license))
                            and m.group(1)
                            if "instances" in license
                            else None
                        ),
                        "is_trial": (
                            (m := re.search(r"is-trial *(\S*)", license)) and m.group(1)
                            if "is-trial" in license
                            else None
                        ),
                        "type": "license",
                    }
            elif "licensing feature" in license:
                licenses_parsed[
                    (m := re.search(r"^ name *(\S*)\s*$", license, flags=re.M))
                    and m.group(1)
                ] = {
                    **(
                        licenses_parsed.get(
                            (m := re.search(r"^ name *(\S*)\s*$", license, flags=re.M))
                            and m.group(1)
                        )
                        or {}
                    ),
                    "licensed_instances": (
                        (m := re.search(r"licensed-instances *(\S*)", license))
                        and m.group(1)
                        if "licensed-instances" in license
                        else None
                    ),
                    "used_instances": (
                        (m := re.search(r"used-instances *(\S*)", license))
                        and m.group(1)
                        if "used-instances" in license
                        else None
                    ),
                    "trial_in_use": (
                        (m := re.search(r"trial-in-use *(\S*)", license)) and m.group(1)
                        if "trial-in-use" in license
                        else None
                    ),
                    "trial_activated": (
                        (m := re.search(r"trial-activated *(\S*)", license))
                        and m.group(1)
                        if "trial-activated" in license
                        else None
                    ),
                    "type": "feature",
                }
        return licenses_parsed

    def get_interface_status(self):
        interfaces_parsed = []
        output = self.send_ssh_command("show interface")
        legacy_blocks = re.findall(
            r"^([A-Za-z0-9/]+) is administratively (\w+), line protocol is (\w+)\s*(.*?)\n(?=\S|$)",
            output,
            flags=re.MULTILINE | re.DOTALL,
        )
        if legacy_blocks:
            for name, admin, proto, tail in legacy_blocks:
                interface_status = {
                    "name": name,
                    "enabled": (admin == "Up"),
                    "link_up": (proto == "Up"),
                }
                if "Radio" in name or "GigabitEthernet" in name or "TenGigE" in name:
                    bw = re.search(r"BW is (\w+)", tail)
                    if bw and bw.group(1) != "Unknown":
                        interface_status["bandwidth"] = bw.group(1)
                interfaces_parsed.append(interface_status)
            return interfaces_parsed
        lines = [l for l in output.splitlines() if l.strip()]
        if not lines:
            return interfaces_parsed
        header_idx = None
        for idx, line in enumerate(lines):
            if re.search(r"\bINTERFACE NAME\b", line) and re.search(r"\bPROTOCOL\s+STATUS\b", line):
                header_idx = idx
                break
        if header_idx is None:
            return interfaces_parsed
        for line in lines[header_idx + 1:]:
            if re.match(r"^-{5,}$", line):
                continue
            m = re.match(
                r"^(?P<name>\S+)\s+(?P<proto>\w+)\s+(?P<phys>\w+)\s+(?P<mac>[0-9A-F:]{17})\s+(?P<speed>\S+(?:\s+\S+)?)\s+(?P<duplex>\S+)\s+(?P<admin>\w+)\s+(?P<reason>.+)?$",
                line,
                flags=re.IGNORECASE,
            )
            if not m:
                continue
            name = m.group("name")
            proto = m.group("proto").lower()
            phys = m.group("phys").lower()
            admin = m.group("admin").lower()
            speed = m.group("speed")
            interface_status = {
                "name": name,
                "enabled": (admin == "up"),
                "link_up": (proto == "up" and phys == "up"),
            }
            if any(x in name for x in ("Radio", "GigabitEthernet", "TenGigE")):
                interface_status["bandwidth"] = speed
            interfaces_parsed.append(interface_status)
        return interfaces_parsed

    def get_rsl(self):
        output = self.send_ssh_command("show radio-carrier status")
        rsl = re.findall(r"^ ?rsl\s+([\d\.-]*) dBm", output, flags=re.M)
        return [float(x) for x in rsl]

    def get_hostname(self):
        if not self.ssh or not self.ssh_channel:
            raise Exception("SSH not initialized.")
        self.send_ssh_command("config")
        output = self.send_ssh_command("show full-configuration system hostname")
        self.send_ssh_command("exit")
        hostname = re.search(r"system hostname (\S*)", output, flags=re.M)
        if hostname:
            hostname = hostname.group(1)
        return hostname

    def get_snmp_community(self):
        if not self.ssh or not self.ssh_channel:
            raise Exception("SSH not initialized.")
        output = self.send_ssh_command("config")
        output += self.send_ssh_command("show full-configuration snmp community")
        output += self.send_ssh_command("exit")
        while not re.match(r"^snmp community \S*", output, flags=re.M):
            time.sleep(0.1)
            if self.ssh_channel.recv_ready():
                output += self.ssh_channel.recv(4096).decode("utf-8")
        community = re.match(r"^snmp community (\S*)", output, flags=re.M)
        if community:
            community = community.group(1)
        return community or "<error>"

    def get_uptime(self):
        if not self.sesh:
            self.web_login()
        with websockets.sync.client.connect(
            f"ws://{self.ip_address}/ie10fix",
            additional_headers={"cookie": f"sesh={self.sesh}"},
            subprotocols=["aurora_channel"],
        ) as ws:
            ws.send(
                """{"token":"%s","message":{"command":6,"data":{"token":"%s"}}}"""
                % (self.sesh.split("-")[0], self.sesh)
            )
            ws.send(bytes.fromhex("0100000001") + b"""{"key":"system_status_1","pluginId":52,"channelId":1}""")
            t = time.monotonic()
            while time.monotonic() - t < UPTIME_CHECK_TIMEOUT:
                msg = ws.recv()
                if not isinstance(msg, bytes) or not (uptime := re.match(br"4\x00\x01\x00\x01(\d*)$", msg)):
                    continue
                try:
                    uptime_val = int(uptime.group(1))
                    self.logger.debug(f"Uptime: {uptime_val}")
                    return uptime_val
                except Exception:
                    raise ValueError("Failed to parse response while checking device uptime.")
            raise Exception("Timed out while checking device uptime.")

    @staticmethod
    def _fetch_link_data_csv():
        response = requests.get(LINK_DATA_URL)
        response.raise_for_status()
        Path(LINK_DATA_CACHE_DIR).mkdir(parents=True, exist_ok=True)
        with open(LINK_DATA_CACHE_FILE, 'w') as file:
            file.write(response.text)

    @staticmethod
    def _load_link_data_csv():
        if Path(LINK_DATA_CACHE_FILE).exists():
            file_mod_time = Path(LINK_DATA_CACHE_FILE).stat().st_mtime
            if time.time() - file_mod_time < LINK_DATA_CACHE_TTL:
                return pd.read_csv(LINK_DATA_CACHE_FILE, dtype=str)
        WTM4000Config._fetch_link_data_csv()
        return pd.read_csv(LINK_DATA_CACHE_FILE, dtype=str)

    @staticmethod
    def _load_link_data(local_site, remote_site):
        df = WTM4000Config._load_link_data_csv()
        result = df[(df['site1'] == local_site) & (df['site2'] == remote_site)]
        if not result.empty:
            return result.iloc[0].to_dict()

    def get_link_data(self):
        if self.site_name and self.remote_site_name:
            if (data := WTM4000Config._load_link_data(self.site_name, self.remote_site_name)) is not None:
                data["site"] = 1
                return data
            if (data := WTM4000Config._load_link_data(self.remote_site_name, self.site_name)) is not None:
                data["site"] = 2
                return WTM4000Config._load_link_data(self.remote_site_name, self.site_name)
        hostname = self.get_hostname()
        if not hostname:
            return None
        for regex in SITE_NAME_REGEXES:
            site_names = re.match(regex, hostname)
            if site_names:
                if (data := WTM4000Config._load_link_data(site_names.group(2), site_names.group(1))) is not None:
                    data["site"] = 1
                    return data
                if (data := WTM4000Config._load_link_data(site_names.group(1), site_names.group(2))) is not None:
                    data["site"] = 2
                    return data

    def check_link(self):
        link_data = self.get_link_data()
        if link_data is None:
            return [("Target RSSI","Could not find link in site data. Is the device named correctly?","",False)]
        results = []
        carrier_status = self.send_ssh_command("show radio-carrier status")
        carriers = list(re.finditer(r"Carrier1/(?P<num>\d).*?bandwidth\s*(?P<bw>\d*\.\d*) MHz.*?current-tx-power\s*(?P<power>-?\d*\.\d*) dBm.*?tx-frequency\s*(?P<tx>\d*) kHz.*?rx-frequency\s*(?P<rx>\d*) kHz.*?remote-rsl\s*(?P<rsl>-?\d*\.\d*) dBm", carrier_status, flags=re.M|re.S))
        if not carriers:
            results.append(("Target RSSI","Failed to get power levels from device.","",False))
        swap_carriers = float(carriers[0]["tx"]) / 1000 != float(link_data.get(f"freq{link_data.get('site')}_1"))
        for i, carrier in enumerate(carriers):
            target_rsl = link_data.get(f"rxmaxPower{link_data.get('site') ^ 3}(dBm)")
            max_power = link_data.get(f"maxPower{link_data.get('site')}(dBm)")
            if not target_rsl or not max_power:
                results.append((f"Target RSSI - Carrier1/{carrier['num']}","Could not find target in site data.","",False))
            target_rsl = float(target_rsl or 0)
            max_power = float(max_power or 0)
            actual_target = (float(carrier["power"]) - max_power) + target_rsl
            error =  float(carrier["rsl"]) - actual_target
            in_range = -2 < error < 0
            if in_range:
                msg = f"{carrier['rsl']} dBm: {error:.2f} dBm off target (in range)"
            elif error > 0:
                msg = f"{carrier['rsl']} dBm: {error:.2f} dBm above target (out of range)"
            else:
                msg = f"{carrier['rsl']} dBm: {error:.2f} dBm off target (out of range)"
            results.append((f"Target RSSI - Carrier1/{carrier['num']}",msg,f"{target_rsl} dBm",in_range))
            other_carrier = list(filter(lambda x: x['num'] != carrier['num'], carriers))[0]
            carrier_num = int(carrier["num"]) ^ 3 if swap_carriers else carrier["num"]
            tx_freq = link_data[f"freq{link_data.get('site')}_{carrier_num}"]
            rx_freq = link_data[f"freq{link_data.get('site') ^ 3}_{carrier_num}"]
            if not (str(tx_freq) == 'nan' and str(rx_freq) == 'nan' and carrier['tx'] == other_carrier['tx'] and carrier['rx'] == other_carrier['rx']):
                results.append((f"Frequencies - Carrier1/{carrier['num']}",f"TX: {int(carrier['tx']) / 1000}, RX: {int(carrier['rx']) / 1000}",f"TX: {tx_freq}, RX: {rx_freq}",int(carrier['tx']) / 1000 == float(tx_freq) and int(carrier['rx']) / 1000 == float(rx_freq)))
            bandwidth = link_data.get(f'planbandwidth{link_data["site"]}(MHz)')
            results.append((f"Bandwidth - Carrier1/{carrier['num']}",f"{bandwidth} MHz",f"{carrier['bw']} MHz",float(bandwidth) == float(carrier['bw'])))
        return results

    def _sfp_status_from_show_interface(self):
        out = self.send_ssh_command("show interface")
        rows = re.findall(
            r"^(?P<name>(?:TenGigE|TenGigabitEthernet|XGE|SFP)\S*)\s+(?P<proto>\w+)\s+(?P<phys>\w+)\s+[0-9A-F:]{17}\s+\S+(?:\s+\S+)?\s+\S+\s+(?P<admin>\w+)",
            out, flags=re.I | re.M
        )
        if rows:
            desc_parts = [f"{r[0]} is {'Up' if (r[1].lower()=='up' and r[2].lower()=='up') else 'Down'}" for r in rows]
            any_up = any((r[1].lower() == "up" and r[2].lower() == "up") for r in rows)
            return {"desc": "; ".join(desc_parts) if desc_parts else "None", "any_up": any_up}
        legacy = re.findall(
            r"^(?P<name>(?:TenGigE|TenGigabitEthernet|XGE|SFP)\S*)\s+is administratively\s+(?P<admin>\w+),\s+line protocol is\s+(?P<proto>\w+)",
            out, flags=re.I | re.M
        )
        if legacy:
            desc_parts = [f"{m[0]} is {'Up' if m[2].lower()=='up' and m[1].lower()=='up' else 'Down'}" for m in legacy]
            any_up = any(m[2].lower() == "up" and m[1].lower() == "up" for m in legacy)
            return {"desc": "; ".join(desc_parts), "any_up": any_up}
        return {"desc": "None", "any_up": None}

    def _detect_device_model(self):
        for cmd in ("show hardware", "show version", "show manufacture-details"):
            try:
                out = self.send_ssh_command(cmd)
            except Exception:
                continue
            m = re.search(r"\bunit-type\s*(WTM\d{4})\b", out, flags=re.I)
            if m:
                return m.group(1)
            m = re.search(r"\bWTM\d{4}\b", out, flags=re.I)
            if m:
                return m.group(0)
        return None
    
    
    def pre_check(self, check_link=False):
        results = []
        if not self.ssh or not self.ssh_channel:
            self.init_ssh()
        interface_status = self.get_interface_status()
        licenses = self.get_licenses()
        for interface in interface_status:
            if "Radio" in interface.get("name"):
                results.append((f"{interface.get('name')} Throughput Capacity", interface.get("bandwidth") or "0", None, None,))
            if "GigabitEthernet" in interface.get("name"):
                results.append((f"{interface.get('name')}", "Link up" if interface.get('link_up') else "Link down", "Link down", not interface.get('link_up')))
        sfp = self._sfp_status_from_show_interface()
        results.append(("SFP Uplink", sfp["desc"], "At least one SFP interface in use", sfp["any_up"],))
    
        fw_version = self.get_firmware_version()
        results.append(("Firmware version", fw_version, ">= " + BASELINE_VERSION, self.version_tuple(fw_version) >= self.version_tuple(BASELINE_VERSION)))
    
        model = self._detect_device_model()
        results.append(("Device model", model, self.radio_type[2], model and self.radio_type[2] in model))
    
        results.append(("SFP Model Number", "Skipped", "Not checked", None))
    
        fw_bundles = self.get_license_bundles()
        if not all((b in fw_bundles for b in self.radio_config["licenses"])):
            fw_bundles = self.get_license_bundles()
        results.append(("License bundle", ", ".join(fw_bundles), ", ".join(self.radio_config["licenses"]), (all((b in fw_bundles for b in self.radio_config["licenses"])) if self.radio_config["licenses"] else None),))
    
        if check_link:
            results += self.check_link()
        return results


    def _send_sensitive_prompt(self, command, secret):
        if not self.ssh or not self.ssh_channel:
            self.init_ssh()
        while self.ssh_channel.recv_ready():
            self.ssh_channel.recv(4096)
        self.ssh_channel.sendall((command + "\n").encode())
        buf = ""
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < SSH_SEND_TIMEOUT:
            if self.ssh_channel.recv_ready():
                buf += self.ssh_channel.recv(4096).decode("ascii", "ignore").replace("\r", "")
                if re.search(r"\(<string\>\):\s*\*+", buf) or re.search(r"\(<string\>\):\s*$", buf, re.M):
                    break
                if re.search(r"syntax error", buf, re.I):
                    raise Exception(buf)
            time.sleep(0.05)
        self.ssh_channel.sendall((secret + "\n").encode())
        out = ""
        t1 = time.perf_counter()
        while time.perf_counter() - t1 < SSH_SEND_TIMEOUT:
            if self.ssh_channel.recv_ready():
                out += self.ssh_channel.recv(4096).decode("ascii", "ignore").replace("\r", "")
                if re.search(r"^\S*#\s", out, re.M):
                    return out
            time.sleep(0.05)
        return out

    def _set_admin_password_610(self):
        target = os.getenv("ADMIN_HASH_610")
        if not target:
            raise ValueError("ADMIN_HASH_610 not set")
        out = ""
        out += self.send_ssh_command("user admin", info_log=True)
        out += self._send_sensitive_prompt("password", target)
        out += self.send_ssh_command("exit", info_log=True)
        return out

    def _send_common_radio_commands(self):
        output = ""
        bw_val = float(self.bandwidth.split(" ")[0])
        if self.template_folder_key == "6.1":
            output += self.send_ssh_command(f"hostname {self.device_name}", info_log=True)
            output += self.send_ssh_command(f"location {self.site_name}", info_log=True)

            output += self.send_ssh_command("radio-link Radio1/1", info_log=True)
            output += self.send_ssh_command("enabled", info_log=True)
            output += self.send_ssh_command("carriers [ Carrier1/1 Carrier1/2 ]", info_log=True)
            output += self.send_ssh_command("mlhc", info_log=True)
            output += self.send_ssh_command("hitless-aggregation", info_log=True)
            output += self.send_ssh_command("a2c-mode fixed-dual-carrier", info_log=True)
            output += self.send_ssh_command("exit", info_log=True)

            output += self.send_ssh_command("radio-carrier Carrier1/1", info_log=True)
            output += self.send_ssh_command("type local-carrier", info_log=True)
            output += self.send_ssh_command("enabled", info_log=True)
            output += self.send_ssh_command(f"bandwidth ANSI {bw_val:.1f}", info_log=True)
            output += self.send_ssh_command(f"tx-frequency {int(self.tx_frequency_v) * 1000}", info_log=True)
            output += self.send_ssh_command(f"rx-frequency {int(self.rx_frequency_v) * 1000}", info_log=True)
            output += self.send_ssh_command(f"power min {self.power_min} max {self.power_max} fade-margin 10.0 fcc-atpc false", info_log=True)
            output += self.send_ssh_command("no tx-mute", info_log=True)
            output += self.send_ssh_command(f"modulation min {self.modulation_min} max {self.modulation_max}", info_log=True)
            output += self.send_ssh_command("exit", info_log=True)

            output += self.send_ssh_command("radio-carrier Carrier1/2", info_log=True)
            output += self.send_ssh_command("type local-carrier", info_log=True)
            output += self.send_ssh_command("enabled", info_log=True)
            output += self.send_ssh_command(f"bandwidth ANSI {bw_val:.1f}", info_log=True)
            output += self.send_ssh_command(f"tx-frequency {int(self.tx_frequency_h) * 1000}", info_log=True)
            output += self.send_ssh_command(f"rx-frequency {int(self.rx_frequency_h) * 1000}", info_log=True)
            output += self.send_ssh_command(f"power min {self.power_min} max {self.power_max} fade-margin 10.0 fcc-atpc false", info_log=True)
            output += self.send_ssh_command("no tx-mute", info_log=True)
            output += self.send_ssh_command(f"modulation min {self.modulation_min} max {self.modulation_max}", info_log=True)
            output += self.send_ssh_command("exit", info_log=True)

            output += self.send_ssh_command("interface Radio1/1", info_log=True)
            output += self.send_ssh_command(f'description {self.device_name}', info_log=True)
            output += self.send_ssh_command("exit", info_log=True)

        else:
            output += self.send_ssh_command(f"system hostname {self.device_name}", info_log=True)
            output += self.send_ssh_command(f'system location "{self.site_name}"', info_log=True)

            output += self.send_ssh_command("interface Carrier1/1", info_log=True)
            output += self.send_ssh_command(f"description {self.device_name}", info_log=True)
            output += self.send_ssh_command(f"bandwidth ANSI {bw_val}", info_log=True)
            self.send_ssh_command("enabled", info_log=True)
            output += self.send_ssh_command("enabled", info_log=True)
            output += self.send_ssh_command(f"tx-frequency {int(self.tx_frequency_v) * 1000}", info_log=True)
            output += self.send_ssh_command(f"rx-frequency {int(self.rx_frequency_v) * 1000}", info_log=True)
            output += self.send_ssh_command(f"coding-modulation adaptive min {self.modulation_min} max {self.modulation_max}", info_log=True)
            output += self.send_ssh_command(f"power atpc selected-min-output-power {self.power_min} selected-max-output-power {self.power_max} fade-margin 10.0", info_log=True)
            output += self.send_ssh_command("no tx-mute", info_log=True)
            output += self.send_ssh_command("exit", info_log=True)

            output += self.send_ssh_command("interface Carrier1/2", info_log=True)
            output += self.send_ssh_command(f"description {self.device_name}", info_log=True)
            output += self.send_ssh_command(f"bandwidth ANSI {bw_val}", info_log=True)
            output += self.send_ssh_command("enabled", info_log=True)
            output += self.send_ssh_command(f"tx-frequency {int(self.tx_frequency_h) * 1000}", info_log=True)
            output += self.send_ssh_command(f"rx-frequency {int(self.rx_frequency_h) * 1000}", info_log=True)
            output += self.send_ssh_command(f"coding-modulation adaptive min {self.modulation_min} max {self.modulation_max}", info_log=True)
            output += self.send_ssh_command(f"power atpc selected-min-output-power {self.power_min} selected-max-output-power {self.power_max} fade-margin 10.0", info_log=True)
            output += self.send_ssh_command("no tx-mute", info_log=True)
            output += self.send_ssh_command("exit", info_log=True)

            output += self.send_ssh_command("interface Radio1", info_log=True)
            output += self.send_ssh_command(f"description {self.device_name}", info_log=True)
            output += self.send_ssh_command("exit", info_log=True)

        return output


    def send_configuration_2_11(self, config):
        if self.readonly:
            raise Exception("Attempted to send configuration in readonly mode.")
        if not self.ssh or not self.ssh_channel:
            self.init_ssh()
        if not self.ssh or not self.ssh_channel:
            raise ConnectionError("Failed to initialize SSH.")
        self.send_ssh_command("config")
        time.sleep(0.2)
        output = ""
        for line in config.split("\n"):
            line = re.sub(r"^ *", r"", line)
            if re.sub(r"\s*", "", line) == "":
                break
            output += self.send_ssh_command(line, info_log=True)
            time.sleep(0.05)
        output += self._send_common_radio_commands()
        if "syntax error" in output:
            self.logger.error(output)
            raise Exception("Syntax error while configuring: %s" % ((m := re.search(r"syntax error: (.*)$", output, flags=re.M)) and m.group(1)))
        output += self.send_ssh_command("commit", info_log=True)
        if "Aborted" in output:
            raise Exception("Commit aborted: %s" % ((m := re.search(r"Aborted: (.*)$", output, flags=re.M)) and m.group(1)))
        wait_start = time.perf_counter()
        while ("Commit complete." not in output and "% No modifications to commit" not in output and time.perf_counter() < wait_start + SSH_SEND_TIMEOUT):
            if self.ssh_channel.recv_ready():
                output += self.ssh_channel.recv(4096).decode("ascii")
            time.sleep(0.1)
        self.logger.info("Configuration complete.")
        self.ssh.close()

    def send_configuration_6_1(self, config):
        if self.readonly:
            raise Exception("Attempted to send configuration in readonly mode.")
        if not self.ssh or not self.ssh_channel:
            self.init_ssh()
        if not self.ssh or not self.ssh_channel:
            raise ConnectionError("Failed to initialize SSH.")
        self.send_ssh_command("config")
        time.sleep(0.2)
        output = ""
        skip_user_block = False
        for raw in config.split("\n"):
            l = re.sub(r"^ *", r"", raw)
            if re.sub(r"\s*", "", l) == "":
                break
            if skip_user_block:
                if l.lower().strip() == "exit":
                    skip_user_block = False
                continue
            if re.match(r"^user\s+admin(?:\s|$)", l, re.I):
                skip_user_block = True
                continue
            output += self.send_ssh_command(l, info_log=True)
            time.sleep(0.05)
        output += self._send_common_radio_commands()
        output += self._set_admin_password_610()
        if "syntax error" in output:
            self.logger.error(output)
            raise Exception("Syntax error while configuring: %s" % ((m := re.search(r"syntax error: (.*)$", output, flags=re.M)) and m.group(1)))
        output += self.send_ssh_command("commit", info_log=True)
        if "Aborted" in output:
            raise Exception("Commit aborted: %s" % ((m := re.search(r"Aborted: (.*)$", output, flags=re.M)) and m.group(1)))
        wait_start = time.perf_counter()
        while ("Commit complete." not in output and "% No modifications to commit" not in output and time.perf_counter() < wait_start + SSH_SEND_TIMEOUT):
            if self.ssh_channel.recv_ready():
                output += self.ssh_channel.recv(4096).decode("ascii")
            time.sleep(0.1)
        self.logger.info("Configuration complete.")
        self.ssh.close()

    def version_tuple(self, v):
        core = re.match(r"\s*([0-9]+(?:\.[0-9]+){0,3})", v)
        if not core:
            return (0, 0, 0, 0)
        parts = [int(x) for x in core.group(1).split(".")]
        while len(parts) < 4:
            parts.append(0)
        return tuple(parts[:4])

    def get_firmware_version(self):
        out = self.send_ssh_command("show version")
        m = re.search(r"software-status\s+active-version\s*([0-9]+\.[0-9]+\.[0-9]+)", out)
        if m:
            return m.group(1)
        m = re.search(r"^\s*([0-9]+\.[0-9]+\.[0-9]+)\s*\(", out, flags=re.M)
        if m:
            return m.group(1)
        return "0.0.0"

    def wait_for_device(self, timeout=1200, sleep_interval=5):
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            try:
                self.init_ssh(force=True, suppress_info_log=True)
                self.logger.info("Device reconnected.")
                return True
            except Exception:
                time.sleep(sleep_interval)
        raise TimeoutError("Timed out waiting for device to reconnect after upgrade.")

    def init_and_configure(self):
        if self.readonly:
            raise Exception("Attempted to configure device in readonly mode.")
        self.init_ssh()
        fw = self.get_firmware_version()
        self._set_template_folder_from_fw(fw)
        precheck_result = self.pre_check()
        self.logger.info(f"Detected firmware: {fw}")
        cur = self.version_tuple(fw)
        base = self.version_tuple(BASELINE_VERSION)
        final = self.version_tuple(FINAL_VERSION)
        if cur < base:
            self.logger.info(f"Firmware below {BASELINE_VERSION}. Starting upgrade to {BASELINE_VERSION}.")
            asyncio.run(self.update_firmware())
            self.logger.info(f"Upgrade to {BASELINE_VERSION} initiated. Waiting for reboot.")
            self.wait_for_device()
            self.logger.info(f"Device running {BASELINE_VERSION} or later.")
            self.init_ssh(force=True)
            fw = self.get_firmware_version()
            self._set_template_folder_from_fw(fw)
        if not DISABLE_PRECHECK and not all([x[3] is not False for x in precheck_result if x[0] != "Firmware version"]):
            raise Exception("Device failed precheck:\n" + "\n".join([f"{x[0]}: expected {x[2]}, actual {x[1] if x[1] else 'None'}" for x in precheck_result if x[3] is False and x[0] != "Firmware version"]) + (("\nNote: Installed license bundles are sometimes incorrectly displayed due to a bug in the backhaul firmware. If this result seems incorrect, try configuring the device again.") if "License bundle" in [x[0] for x in precheck_result if x[3] is False] else ""))
        self._enforce_frequency_limits_4200()
        try:
            cfg = self.get_standard_config()
            if self.template_folder_key == "6.1":
                self.send_ssh_command("config")
                self.send_configuration_6_1(cfg)
            else:
                self.send_ssh_command("config")
                self.send_configuration_2_11(cfg)
        except FileNotFoundError as err:
            raise Exception("Could not read base configuration: %s" % (err)) from err
        self.init_ssh(force=True)
        current_after_config = self.get_firmware_version()
        self.logger.info(f"Post-config firmware: {current_after_config}")
        if self.version_tuple(current_after_config) < final:
            self.logger.info(f"Upgrading to {FINAL_VERSION}.")
            self.update_firmware_from_server(uri=FINAL_FIRMWARE_URI, activate_now=True)
            self.logger.info("Upgrade started. Waiting for reboot.")
            self.wait_for_device()
            self.logger.info(f"Device upgrade to {FINAL_VERSION} complete.")
            self.init_ssh(force=True)
        else:
            self.logger.info(f"Device already at {FINAL_VERSION}. Skipping firmware upgrade.")

    def web_login(self):
        if not self.req_session:
            self.req_session = requests.Session()
        passwords = []
        if self.ssh_password:
            passwords.append(self.ssh_password)
        passwords += PASSWORDS
        login_req = None
        for pw in passwords:
            try:
                login_req = self.req_session.post(
                    f"http://{self.ip_address}/wtmlogin",
                    data={"username": "admin", "password": pw},
                    timeout=LOGIN_TIMEOUT,
                )
                if login_req.status_code == 200:
                    break
            except Exception:
                continue
        if (not login_req or login_req.status_code != 200 or not login_req.cookies.get("sesh")):
            raise ConnectionError("Web interface login failed.")
        self.sesh = login_req.cookies["sesh"]

    def upload_firmware_file(self, file_path):
        if self.readonly:
            raise Exception("Attempted to upload firmware file in readonly mode.")
        if not self.sesh:
            self.web_login()
        if not self.req_session or not self.sesh:
            raise Exception("Session not initialized")
        file = pathlib.Path(file_path)
        if not file.exists():
            raise FileNotFoundError("Could not find firmware file.")
        if file.is_dir():
            raise FileNotFoundError("Specified path is a directory.")
        with file.open(mode="rb") as f:
            files = {"file": (file.name, f)}
            upload_req = self.req_session.post(f"http://{self.ip_address}/admin/swload/upload", files=files)
        if upload_req.status_code != 200:
            raise ConnectionError("Failed to upload firmware file.")

    async def update_firmware(self, firmware=None):
        if self.readonly:
            raise Exception("Attempted to update firmware file in readonly mode.")
        if not self.sesh:
            self.web_login()
        if not self.req_session or not self.sesh:
            raise Exception("Session not initialized")
        firmware = firmware or RADIO_FIRMWARE[self.device_type]
        self.logger.info("Uploading firmware file...")
        self.upload_firmware_file(firmware["file"])
        self.logger.info("Uploaded firmware.")
        async with websockets.connect(
            f"ws://{self.ip_address}/ie10fix",
            extra_headers={"cookie": f"sesh={self.sesh}"},
            subprotocols=["aurora_channel"],
        ) as ws:
            t = time.monotonic()
            while time.monotonic() < t + 2:
                try:
                    time.sleep(1)
                except Exception as e:
                    continue
            self.logger.info("Installing update...")
            await ws.send("""{"token":"%s","message":{"command":6,"data":{"token":"%s"}}}""" % (self.sesh.split("-")[0], self.sesh))
            time.sleep(1)
            await ws.send(bytes.fromhex("45000100") + b"""{"command":7,"value":"begin","file":"%s","progress":0,"total":100}""" % firmware["filename"].encode("utf-8"))
            for i in [20 * x - 1 for x in range(6)]:
                time.sleep(1)
                await ws.send(bytes.fromhex("45000100") + ("""{"command":7,"value":"begin","file":"%s","progress":%s,"total":%d}""" % (firmware["filename"], str(int(firmware["size"] / 10 * (i + 1))), firmware["size"],)).encode("utf-8"))
            for i in range(5):
                await ws.send(bytes.fromhex("01000700") + b"""heartbeat""")
                time.sleep(2)
            time.sleep(6)
            await ws.send(bytes.fromhex("45000100") + b"""{"command":3,"remote":false}""")
            self.logger.info("Waiting for device to complete install and reboot.")
            while True:
                try:
                    async with asyncio.timeout(1):
                        await ws.send(bytes.fromhex("01000700") + b"""heartbeat""")
                        time.sleep(1)
                        await ws.recv()
                    time.sleep(1)
                except Exception as err:
                    time.sleep(1)
                    break
            time.sleep(200)
            while True:
                try:
                    self.web_login()
                except Exception as err:
                    continue
                break
        time.sleep(4)
        self.init_ssh(force=True)

    def update_firmware_from_server(self, uri=None, activation_time=None, activate_now=True):
        if not self.ssh:
            self.init_ssh()
        uri = uri or DEFAULT_FIRMWARE_URI
        uptime = self.get_uptime()
        if uptime >= FW_UPLOAD_MAX_UPTIME:
            raise Exception(f"The device's uptime is greater than {int(FW_UPLOAD_MAX_UPTIME / 86400)} days. Uploading a firmware image may cause an unexpected reboot.")
        self.logger.info("Sending update command.")
        result = ""
        if activate_now:
            result = self.send_ssh_command(f"software load uri {uri} force activation-immediately")
        else:
            if activation_time:
                result = self.send_ssh_command(f"software load uri {uri} force activation-time {activation_time}")
            else:
                result = self.send_ssh_command(f"software load uri {uri} force")
        if "Loading started with" not in result:
            resp_filtered = re.findall(r"resp (.*?)\n", result)
            raise Exception(resp_filtered[0] if resp_filtered else result)
        self.logger.info("Update started." if activate_now else "Firmware download started.")

    def activate_firmware(self):
        if not self.ssh:
            self.init_ssh()
        self.logger.info("Sending software activation command.")
        result = self.send_ssh_command("software activate")
        if "resp Activating new software now" not in result:
            resp_filtered = re.findall(r"resp (.*?)\n", result)
            raise Exception(resp_filtered[0] if resp_filtered else result)
        else:
            self.logger.info("Activation started.")

    @staticmethod
    def get_device_info(ip_address, device_type, password=None, run_tests=False):
        result = {}
        params = {
            "ip_address": ip_address,
            "device_type": device_type,
            "link_type": "dummy",
            "xpic": True,
        }
        if password:
            params['password'] = password
        w = WTM4000Config(**params, readonly=True)
        w.init_ssh()
        carrier_status = w.send_ssh_command("show radio-carrier status")
        interfaces = w.send_ssh_command("show interface")
        running_config = result["running_config"] = w.get_running_config(json_conf=True, paths=True)
        running_config = sorted([f"{'no ' if x['value'] is False else ''}{x['path']}{' ' + x['value'] if not isinstance(x['value'], bool) else ''}" for x in running_config])
        result["running_config"] = "\n".join(running_config)
        w.send_ssh_command("config")
        radio_config = w.send_ssh_command("show full-configuration interface Radio1")
        w.send_ssh_command("exit")
        carrier_frequencies = re.findall(r"(Carrier1/\d).*?tx-frequency\s*(\d*)\skHz\s\srx-frequency\s*(\d*) kHz", carrier_status, flags=re.M|re.S)
        if not carrier_frequencies:
            raise Exception("Failed to determine carrier frequencies.")
        result["carriers"] = [{"carrier": x[0],"tx_frequency": x[1],"rx_frequency": x[2]} for x in carrier_frequencies]
        xpic_status = re.findall(r"xpic\s*(\w*)", radio_config, flags=re.M|re.S)
        if not xpic_status:
            raise Exception("Failed to determine XPIC status.")
        result["xpic"] = xpic_status[0]
        if not interfaces:
            raise Exception("Failed to read interfaces.")
        result["has_l1la"] = "L1LA1 is administratively Up" in interfaces
        result["link_type"] = {"local": "2_0","horizontal": "4_0_H","vertical": "4_0_V",}.get(result["xpic"], "2_0")
        w.use_xpic = result["xpic"] in ("local", "horizontal", "vertical")
        radio_config_item = None
        for config in RADIO_CONFIGS[device_type]["xpic" if w.use_xpic else "non-xpic"]:
            if config["keyword"] == result["link_type"]:
                radio_config_item = config
                break
        try:
            if radio_config_item:
                w.radio_config = radio_config_item
                standard_config = w.get_standard_config(json_conf=True, paths=True)
                standard_config = sorted([f"{'no ' if x['value'] is False else ''}{x['path']}{' ' + x['value'] if not isinstance(x['value'], bool) else ''}" for x in standard_config])
                result["standard_config"] = "\n".join(standard_config)
            else:
                result["config_error"] = "Detected link type is not supported. Is the device model correct?"
            if device_type == "AV4200":
                try:
                    result["variant"] = w._detect_4200_variant()
                except Exception:
                    result["variant"] = None
            if run_tests:
                result["test_results"] = [{"name": x[0], "expected": x[2], "actual": x[1], "pass": x[3]} for x in w.pre_check(check_link=True)]
                w.close_session()
            result["success"] = True
        except Exception as err:
            try:
                w.close_session()
            except Exception:
                pass
            result["success"] = False
            result["message"] = err
        return result


    @staticmethod
    def request_params(default_params={}, use_default=False, **params):
        if default_params is None:
            default_params = {}
        if params.get("device_type") is not None:
            params["radio_type"] = get_item(params.get("device_type"), RADIO_MODELS)
        if params.get("radio_type") is None:
            params["radio_type"] = prompt_list("Select device type: ",RADIO_MODELS,default=default_params.get("radio_type") or 0,)
        if params.get("config_file") is None:
            params["config_file"] = prompt_list("Select radio configuration: ",RADIO_CONFIGS.get(params["radio_type"][1]),default=default_params.get("config_file") or 0,)
        if params.get("ip_address") is None:
            params["ip_address"] = input_default("[?] IP Address (incl. CIDR, if required; default /29): ",default_params.get("ip_address"),use_default=use_default,)
        if "/" in params["ip_address"]:
            params["ip_address"], cidr = params["ip_address"].split("/")
            params["subnet_mask"] = calc_netmask(int(cidr))
        else:
            params["subnet_mask"] = "255.255.255.248"
        if params.get("site_name") is None:
            params["site_name"] = input_default("[?] Local site name: ", default_params.get("site_name"), use_default)
        if params.get("remote_site_name") is None:
            params["remote_site_name"] = input_default("[?] Remote site name: ", default_params.get("remote_site_name"), use_default,)
        if params.get("tx_frequency") is None:
            params["tx_frequency"] = input_default("[?] TX Frequency: ", default_params.get("tx_frequency"), use_default)
        if params.get("rx_frequency") is None:
            params["rx_frequency"] = input_default("[?] RX Frequency: ", default_params.get("rx_frequency"), use_default)
        if params.get("bandwidth") is None:
            params["bandwidth"] = prompt_list("Enter bandwidth (MHz): ",BANDWIDTHS,default_params.get("bandwidth") or "80 MHz",use_default,)
        if params.get("modulation_min") is None:
            params["modulation_min"] = prompt_list("Enter min. modulation: ",MODULATION_MIN,default_params.get("modulation_min"),use_default,)
        if params.get("modulation_max") is None:
            params["modulation_max"] = prompt_list("Enter max. modulation: ",MODULATION_MAX,default_params.get("modulation_max"),use_default,)
        if params.get("power_min") is None:
            params["power_min"] = float(input_default("[?] Min. Output Power (%.01f-%.01f dBm): " % (MIN_POWER_RANGE[0], MIN_POWER_RANGE[1]),default=default_params.get("power_min"),use_default=use_default,))
        if (float(params["power_min"]) < MIN_POWER_RANGE[0] or float(params["power_min"]) > MIN_POWER_RANGE[1]):
            raise ValueError("%.01f out of range: %.01f-%.01f dBm" % (float(params["power_min"]),MIN_POWER_RANGE[0],MIN_POWER_RANGE[1],))
        else:
            params["power_min"] = "%.01f" % float(params["power_min"])
        if params.get("power_max") is None:
            params["power_max"] = float(input_default("[?] Max. Output Power (%.01f-%.01f dBm): " % (MAX_POWER_RANGE[0], MAX_POWER_RANGE[1]),default=default_params.get("power_max"),use_default=use_default,))
        if (float(params["power_max"]) < MAX_POWER_RANGE[0] or float(params["power_max"]) > MAX_POWER_RANGE[1]):
            raise ValueError("%.01f out of range: %.01f-%.01f dBm" % (float(params["power_max"]),MAX_POWER_RANGE[0],MAX_POWER_RANGE[1],))
        else:
            params["power_max"] = "%.01f" % float(params["power_max"])
        if params.get("rsl_max") is None:
            params["rsl_max"] = input("[?] Maximum backhaul RSL (per PCN): ")
        params["name"] = "BH-%s-%d-%s.%s" % (params["radio_type"][1],int(round(float(params["tx_frequency"]) / 1000)),params.get("remote_site_name"),params.get("site_name"),)
        return params

def main():
    def parse_cli_args(args, delimiter=" "):
        if isinstance(args, str):
            args = args.split(delimiter)
        result = {}
        while len(args) > 0:
            if "-" not in args[0]:
                args.pop(0)
            else:
                val = args[0].split("=")[0]
                if val == "-d" or val == "--device-type":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["device_type"] = args[0]
                elif val == "-c" or val == "--config":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["config_file"] = get_item(args[0],RADIO_CONFIGS[get_item(result.get("device_type"), RADIO_MODELS)[1]],)
                elif val == "-i" or val == "--ip-address":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["ip_address"] = args[0]
                elif val == "-s" or val == "--ssh-password":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["ssh_password"] = args[0]
                elif val == "-n" or val == "--site-name":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["site_name"] = args[0]
                elif val == "-R" or val == "--remote-site":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["remote_site_name"] = args[0]
                elif val == "-t" or val == "--tx-frequency":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["tx_frequency"] = args[0]
                elif val == "-r" or val == "--rx-frequency":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["rx_frequency"] = args[0]
                elif val == "-b" or val == "--bandwidth":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["bandwidth"] = get_item(args[0], BANDWIDTHS)
                elif val == "-m" or val == "--modulation-min":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["modulation_min"] = get_item(args[0], MODULATION_MIN)
                elif val == "-M" or val == "--modulation-max":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["modulation_max"] = get_item(args[0], MODULATION_MAX)
                elif val == "-p" or val == "--power-min":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    if (float(args[0]) > MIN_POWER_RANGE[0] and float(args[0]) < MIN_POWER_RANGE[1]):
                        result["power_min"] = args[0]
                    else:
                        raise ValueError("%.01f out of range: %.01f-%.01f dBm" % (float(args[0]), MIN_POWER_RANGE[0], MIN_POWER_RANGE[1]))
                elif val == "-P" or val == "--power-max":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    if (float(args[0]) > MAX_POWER_RANGE[0] and float(args[0]) < MAX_POWER_RANGE[1]):
                        result["power_max"] = args[0]
                    else:
                        raise ValueError("%.01f out of range: %.01f-%.01f dBm" % (float(args[0]), MAX_POWER_RANGE[0], MAX_POWER_RANGE[1]))
                elif val == "-h" or val == "--help":
                    print(HELP_MESSAGE)
                    exit()
        return result

    wtm = WTM4000Config(**WTM4000Config.request_params(**parse_cli_args(sys.argv)))
    wtm.init_and_configure()

if __name__ == "__main__":
    main()
