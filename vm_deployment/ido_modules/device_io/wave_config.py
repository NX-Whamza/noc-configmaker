import re
import os
import time
import logging
import json
import platform
import subprocess
import urllib3
import requests
from .util import get_item, ConfigLogFormatter, parsepath
import paramiko
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import traceback
import socket
from threading import Semaphore, Lock

from .mac import mac_query_variants, normalize_mac

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BNG_SSH_SEMAPHORE = Semaphore(3)
_BNG_CACHE = {}
_BNG_CACHE_LOCK = Lock()
DEBUG = os.getenv("NETLAUNCH_TOOLS_DEBUG", False)

DEVICE_TYPES = [
    {
        "name": "Wave AP",
        "model": "Wave-AP",
        "identifier": "WAP",
        "category": "AP",
        "firmware_standard": "3.4.0"
    },
    {
        "name": "Wave AP Micro",
        "model": "Wave-AP-Micro",
        "identifier": "WAPM",
        "category": "AP",
        "firmware_standard": "3.4.0"
    }
]

LOGINS = {
    "AP": [
        {"username": "admin", "password": os.getenv("WAVE_AP_PASS", "")},
        {"username": "ubnt", "password": "ubnt"},
        {"username": "ubnt", "password": os.getenv("WAVE_AP_PASS", "")},
    ],
}

BASE_CONFIG_FILES = {
    "Wave-AP": os.getenv("BASE_CONFIG_PATH", "")
    + "/Ubiquiti/Wave/config.json",
    "Wave-AP-Micro": os.getenv("BASE_CONFIG_PATH", "")
    + "/Ubiquiti/Wave Micro/config.json",
}

# Config files matching the format stored at /mnt/persistent/config.json
FULL_CONFIG_FILES = {
    "Wave-AP": os.getenv("BASE_CONFIG_PATH", "")
    + "/Ubiquiti/Wave/full_config.json",
    "Wave-AP-Micro": os.getenv("BASE_CONFIG_PATH", "")
    + "/Ubiquiti/Wave Micro/full_config.json",
}

with open(os.getenv("BNG_SSH_SERVER_CONFIG", ""), "r") as f:
    SSH_SERVERS = json.load(f)

SMAP_KEY = os.getenv("SMAP_KEY")

FIRMWARE_FILES = {
    "Wave-AP": (
        os.getenv("FIRMWARE_PATH", "")
        + "/Ubiquiti/Wave/MGMP.ipq807x.v3.4.0.cd580eac.241001.1121.bin"
    ),
    "Wave-AP-Micro": (
        os.getenv("FIRMWARE_PATH", "")
        + "/Ubiquiti/Wave/MGMP.ipq807x.v3.4.0.cd580eac.241001.1121.bin"
    ),
}

ANTENNAS = {
        "Wave-AP": [{"name": "UB030"}],
        "Wave-AP-Micro": [{"name": "UB090"}]
        }

BANDWIDTHS = [20, 40, 80]

VALID_FREQUENCIES = {
        20: [*range(5180, 5321, 5), *range(5485, 5841, 5)],
        40: [*range(5190, 5311, 5), *range(5495, 5831, 5)],
        80: [*range(5210, 5291, 5), *range(5515, 5811, 5)]
        }

MIN_POWER_EIRP = 17
MAX_POWER_EIRP = 41

UPGRADE_TIMEOUT = 120
REBOOT_TIMEOUT = 300
LOGIN_TIMEOUT = 30
CONFIG_TIMEOUT = 60

MGMT_VLAN = 3000

DEFAULT_BANDWIDTH = 20
DEFAULT_POWER = 39

RUNNING_CONFIG_ENDPOINTS = [
        "/system/airos/configuration",
        "/services"
        ]


class WaveConfig:
    def __init__(self, logstream=None, readonly=False, **params):
        self.params = params
        self.readonly = readonly

        self.gateway = params.get("gateway")
        self.target_ip_address = params.get("target_ip_address")
        self.ip_address = params["ip_address"]
        if not re.match(r"^\d{1,3}(?:\.\d{1,3}){3}(?:\/\d{1,2})?$", self.ip_address):
            raise ValueError("Invalid value for parameter ip_address.")

        use_dhcp_val = params.get("use_dhcp", False)
        self.use_dhcp = (isinstance(use_dhcp_val, bool) and use_dhcp_val is True) or use_dhcp_val == "true"

        if self.use_dhcp:
            self.mac_address = normalize_mac(params.get("mac_address"))
            if not self.ip_address or "/" not in self.ip_address:
                raise ValueError("CIDR is required for devices using DHCP.")
            self.config_ip_cidr = self.ip_address.strip()
            if self.target_ip_address and re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", self.target_ip_address.strip()):
                self.ip_address = self.target_ip_address.strip()
            else:
                self.ip_address = None
            if not self.gateway:
                self.gateway = params["gateway"]
        else:
            if self.target_ip_address and re.match(r"^\d{1,3}(?:\.\d{1,3}){3}\/\d{1,2}$", self.target_ip_address.strip()):
                self.config_ip_cidr = self.target_ip_address.strip()
            elif "/" in self.ip_address and re.match(r"^\d{1,3}(?:\.\d{1,3}){3}\/\d{1,2}$", self.ip_address.strip()):
                self.config_ip_cidr = self.ip_address.strip()
            else:
                raise ValueError("CIDR is required for configuration payload.")
            self.ip_address = self.ip_address.split("/")[0].strip()

        self.password = params.get("password", None)

        self.logger = logging.getLogger(__name__ + f"_{self.ip_address or 'dhcp'}")
        if logstream:
            log_handler = logging.StreamHandler(logstream)
            log_handler.setFormatter(ConfigLogFormatter())
            log_handler.setLevel(logging.INFO)
            self.logger.addHandler(log_handler)

        self.device_type = params.get("ap_type", get_item(params.get("device_type"), DEVICE_TYPES))
        self.antenna = ANTENNAS[self.device_type["model"]][0]
        self.device_category = self.device_type["category"]

        try:
            self.base_config = BASE_CONFIG_FILES[self.device_type["model"]]
            self.full_config = FULL_CONFIG_FILES[self.device_type["model"]]
            self.firmware = FIRMWARE_FILES[self.device_type["model"]]

            if self.readonly:
                self.azimuth = ""
                self.site_name = ""
                self.device_number = ""
                self.height = ""
                self.bandwidth = ""
                self.frequency = ""
                self.power_eirp = ""
            else:
                self.site_name = params["site_name"]
                self.azimuth = str(int(params["azimuth"].strip()) % 360).zfill(3)
                self.device_number = str(params.get("device_number", "1"))
                self.height = params["height"]

                self.bandwidth = int(params.get("bandwidth", DEFAULT_BANDWIDTH))
                if int(self.bandwidth) not in BANDWIDTHS:
                    raise ValueError("Invalid value for bandwidth.")

                self.frequency = int(params["frequency"])
                if self.frequency not in VALID_FREQUENCIES[self.bandwidth]:
                    raise ValueError("Invalid value for frequency.")

                self.power_eirp = int(params.get("power", DEFAULT_POWER))
                if self.power_eirp > MAX_POWER_EIRP or self.power_eirp < MIN_POWER_EIRP:
                    raise ValueError("Invalid value for power.")
        except KeyError as err:
            if not readonly:
                raise KeyError(f"Invalid value: {err}.") from None

        self.session = None
        self.headers = {}

    def wait_until_port_open(self, ip=None, port=443, init_delay=0, timeout=300, interval=1.5):
        host = (ip or self.ip_address or "").split("/")[0]
        time.sleep(init_delay)
        end = time.time() + timeout
        while time.time() < end:
            try:
                with socket.create_connection((host, port), timeout=3):
                    return True
            except OSError:
                time.sleep(interval)
        return False

    def configure_with_bank_check(self, status_cb=lambda s: None):
        if self.readonly:
            raise Exception("Attempted to configure device in readonly mode.")
        status_cb("Login")
        self.init_session()
        status_cb("Pre-check")
        self.enable_ssh_services()
        time.sleep(1.0)
        active_ver, backup_ver = self.get_firmware_banks_via_ssh()
        target = self.device_type["firmware_standard"]
        status_cb(f"FW Banks A:{active_ver or '?'} B:{backup_ver or '?'}")
        up_count = self.decide_upgrade_count(active_ver, backup_ver, target)
        for i in range(up_count):
            status_cb(f"Firmware Upgrade {i+1}/{up_count}")
            self.update_firmware()
        status_cb("Push Config")
        self.upload_configuration()
        status_cb("Done")

    def enable_ssh_services(self):
        if not self.session:
            self.init_session()
        headers = {**self.headers, "Accept": "application/json"}
        r = self.session.get(f"https://{self.ip_address}/api/v1.0/services", headers=headers, verify=False, timeout=30)
        if not r.ok:
            raise ConnectionError("Failed to read services.")
        services = r.json()
        services.setdefault("sshServer", {})
        services["sshServer"]["enabled"] = True
        services["sshServer"]["passwordAuthentication"] = True
        services["sshServer"]["sshPort"] = 22
        payload = {"requests":[{"body":services,"method":"PUT","route":"/services"}],"rollback":{"onError":True,"onUnreachable":{}}}
        headers = {**self.headers, "Content-Type":"application/json","Accept":"application/json"}
        r2 = self.session.post(f"https://{self.ip_address}/api/v1.0/tools/compose", headers=headers, json=payload, verify=False, timeout=60)
        if not r2.ok:
            raise ConnectionError("Failed to enable SSH services.")

    def get_firmware_banks_via_ssh(self):
        import socket
        BASH_SCRIPT = r"""
    MOUNTPOINT=/tmp/__partition
    FLAVOR=$(cat /usr/lib/flavor)
    boot_part=$(fw_printenv boot_part 2>/dev/null | cut -d= -f2)
    if [ "$FLAVOR" = GMC ]; then
        [ "$boot_part" = 0 ] && PART_DEV=/dev/mmcblk0p2 || PART_DEV=/dev/mmcblk0p1
        mkdir -p $MOUNTPOINT
        mount -o ro $PART_DEV $MOUNTPOINT 2>/dev/null || { echo ACTIVE=$(cat /usr/lib/version); echo BACKUP=; exit 0; }
        echo ACTIVE=$(cat /usr/lib/version)
        echo BACKUP=$(cat $MOUNTPOINT/usr/lib/version 2>/dev/null)
        umount $MOUNTPOINT
        rm -rf $MOUNTPOINT
        exit 0
    fi
    MTD0=$(grep '"system0"' /proc/mtd | sed 's/mtd\([0-9]\+\):.*/\1/')
    MTD1=$(grep '"system1"' /proc/mtd | sed 's/mtd\([0-9]\+\):.*/\1/')
    echo ACTIVE=$(cat /usr/lib/version)
    INACTIVE_MTD=$([ "$boot_part" = 1 ] && echo $MTD0 || echo $MTD1)
    UBI_DEV=$(ubinfo -a -m $INACTIVE_MTD 2>/dev/null | awk -F: '/ubi[0-9]+/{sub("ubi","",$1);print $1}')
    did_attach=0
    if [ -z "$UBI_DEV" ]; then
        UBI_DEV=$(ubiattach /dev/ubi_ctrl -m $INACTIVE_MTD 2>/dev/null | awk '/UBI device number/ {print $4}' | tr -d ,)
        [ -z "$UBI_DEV" ] && echo BACKUP= && exit 0
        did_attach=1
    fi
    UBI_PATH=/dev/ubi${UBI_DEV}_1
    mkdir -p $MOUNTPOINT
    mount -t ubifs -o ro $UBI_PATH $MOUNTPOINT 2>/dev/null || { echo BACKUP=; [ "$did_attach" = 1 ] && ubidetach /dev/ubi_ctrl -d $UBI_DEV 2>/dev/null; exit 0; }
    echo BACKUP=$(cat $MOUNTPOINT/lib/version 2>/dev/null)
    umount $MOUNTPOINT
    [ "$did_attach" = 1 ] && ubidetach /dev/ubi_ctrl -d $UBI_DEV 2>/dev/null
    rm -rf $MOUNTPOINT
    """
        username = self.login["username"]
        password = self.login["password"]
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        end = time.time() + 60
        last_err = None
        while time.time() < end:
            try:
                client.connect(self.ip_address, username=username, password=password, timeout=15, look_for_keys=False, allow_agent=False)
                break
            except Exception as e:
                last_err = e
                time.sleep(2)
        if not client.get_transport() or not client.get_transport().is_active():
            raise ConnectionError(f"SSH connect failed: {last_err}")
        stdin, stdout, _ = client.exec_command("sh -s", timeout=120)
        stdin.write(BASH_SCRIPT)
        stdin.close()
        out = stdout.read().decode()
        client.close()
        def _short(s):
            m = re.search(r"\bv(\d+\.\d+\.\d+)", s or "")
            return m.group(1) if m else (s or "")
        a = re.search(r"ACTIVE=([^\s]+)", out)
        b = re.search(r"BACKUP=([^\s]+)", out)
        return _short(a.group(1) if a else ""), _short(b.group(1) if b and b.group(1) else "")

    @staticmethod
    def _ver_tuple(v):
        try:
            parts = [int(x) for x in (v or "").split(".")]
            while len(parts) < 3:
                parts.append(0)
            return tuple(parts[:3])
        except Exception:
            return (0,0,0)

    def decide_upgrade_count(self, active, backup, target):
        ta = self._ver_tuple(target)
        aa = self._ver_tuple(active)
        bb = self._ver_tuple(backup)
        if aa >= ta and bb >= ta:
            return 0
        if aa >= ta and bb < ta:
            return 1
        return 2

    def get_dhcp_ip_address(self):
        if not self.use_dhcp or not self.mac_address:
            raise ValueError("Attempted to get DHCP address for device not using DHCP.")

        mac_address_lower = normalize_mac(self.mac_address)
        if not mac_address_lower:
            raise ValueError("Attempted to get DHCP address with empty MAC address.")

        with _BNG_CACHE_LOCK:
            cached = _BNG_CACHE.get(mac_address_lower)
        if cached:
            self.ip_address = cached
            return self.ip_address

        try:
            BNG_SSH_SEMAPHORE.acquire()
            for server in SSH_SERVERS:
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(hostname=server["hostname"], port=server["port"], username=server["username"], password=server["password"], timeout=10, look_for_keys=False, allow_agent=False)
                    shell = ssh.invoke_shell()
                    time.sleep(2); shell.recv(9999)
                    shell.send(f"show service id 300 dhcp lease-state | match context all {mac_address_lower}\n")
                    time.sleep(3)
                    output = shell.recv(99999).decode("utf-8", errors="ignore").strip()
                    ssh.close()
                    m = re.search(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s", output or "", re.MULTILINE)
                    if m:
                        ip = m.group(1)
                        with _BNG_CACHE_LOCK:
                            _BNG_CACHE[mac_address_lower] = ip
                        self.ip_address = ip
                        return self.ip_address
                except Exception:
                    continue
        finally:
            try:
                BNG_SSH_SEMAPHORE.release()
            except Exception:
                pass

        try:
            api_url = "http://smap-db-dev.nxlink.com/API/get_ip_mac_current"
            headers = {"Authorization": SMAP_KEY, "Content-Type": "application/json"}
            for q in (v.upper() for v in mac_query_variants(mac_address_lower)):
                payload = {"query": q}
                resp = requests.post(api_url, headers=headers, json=payload, timeout=5)
                if not resp.ok:
                    continue
                data = resp.json()
                if "get_ip_mac_current" not in data or len(data["get_ip_mac_current"]) == 0:
                    continue
                ip = data["get_ip_mac_current"][0].get("ip")
                if not ip:
                    continue
                ip = str(ip).strip()
                with _BNG_CACHE_LOCK:
                    _BNG_CACHE[mac_address_lower] = ip
                self.ip_address = ip
                return self.ip_address
        except Exception:
            pass

        raise Exception(f"Failed to determine IP address for MAC address {self.mac_address}.")

    def init_session(self):
        self.session = requests.Session()
        if not self.session:
            raise Exception("Failed to initialize session.")
        if not self.ip_address:
            self.get_dhcp_ip_address()
            self.logger.info(f"Found device with IP address {self.ip_address}")
        base_logins = LOGINS[self.device_category]
        logins = list(base_logins)
        if self.params.get("password"):
            logins = [{"username": self.params.get("username", "admin"), "password": self.params["password"]}] + logins
        url = f"https://{self.ip_address}/api/v1.0/user/login"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        end = time.time() + LOGIN_TIMEOUT
        last_err = None
        while time.time() < end and not self.headers:
            for login in logins:
                try:
                    resp = self.session.post(url, headers=headers, json=login, verify=False, timeout=10)
                    if resp.ok:
                        self.logger.info("Logged in.")
                        self.headers = {"x-auth-token": resp.headers.get("x-auth-token")}
                        self.login = login
                        break
                    last_err = Exception(f"HTTP {resp.status_code}")
                except requests.exceptions.RequestException as e:
                    last_err = e
                    time.sleep(1)
            if not self.headers:
                time.sleep(1)
        if not self.headers:
            if last_err:
                self.logger.debug(f"Login failed: {last_err}")
            raise ValueError("Invalid login credentials or device not ready.")

    def logout(self):
        """Log out of device."""
        if not self.session:
            return

        resp = self.session.post(f"https://{self.ip_address}/api/v1.0/user/logout", verify=False, headers=self.headers)

        if resp.status_code != 200:
            raise Exception(f"Failed to log out with status code {resp.status_code}.")

    def init_and_configure(self):
        if self.readonly:
            raise Exception("Attempted to configure device in readonly mode.")

        self.init_session()

        # Check if device is out of date, and if so, update
        precheck_result = self.pre_check()

        if not (
            model_result := [x for x in precheck_result if x[0] == "Device Model"]
        ):
            raise ConnectionError("Could not determine device model.")

        if not model_result[0][3]:
            raise Exception("Incorrect device model selected.")

        if not (
            fw_result := [x for x in precheck_result if x[0] == "Firmware Version"]
        ):
            self.logger.warning("Could not determine firmware version.")
        
        self.logger.debug(fw_result)
        if not fw_result[0][3]:
            self.logger.info("Firmware out of date.")
            self.update_firmware()

        # Update second bank, even if already up to date
        self.logger.info("Updating second bank...")
        self.update_firmware()
        self.logger.info("Uploading configuration...")
        self.upload_configuration()

        self.logger.info(
            "\nConfiguration finished."
        )

    def upload_configuration(self):
        if self.readonly:
            raise Exception("Attempted to update config in readonly mode.")
        if not self.session:
            self.init_session()
        if not self.session:
            raise Exception()

        base_config = self.get_standard_config()

        headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            config_result = self.session.post(
                f"https://{self.ip_address}/api/v1.0/tools/compose",
                headers=headers,
                json=base_config,
                verify=False,
                timeout=CONFIG_TIMEOUT
            )
            self.logger.debug(config_result.content)
            if not all((r.get("statusCode") == 200 for r in config_result.json().get("responses"))):
                raise Exception(f"Configuration failed: config_result.content")
        except requests.exceptions.Timeout:
            self.logger.debug("Configuration timed out.")
            if not self.use_dhcp:
                raise ConnectionError("Configuration timed out.")
            new_ip = (self.config_ip_cidr or "").split("/")[0]
            if not self.ping_device(ip=new_ip):
                raise ConnectionError("Configuration failed: device unreachable.")
        except Exception as err:
            raise ConnectionError(err)

        if self.use_dhcp:
            new_ip = (self.config_ip_cidr or "").split("/")[0]
            self.ip_address = new_ip
            self.use_dhcp = False
            self.session = None
            self.headers = {}
            if not self.wait_until_ping(self.ip_address, init_delay=2, timeout=90):
                raise TimeoutError("Device did not answer ping after IP change.")
            if not self.wait_until_port_open(self.ip_address, port=443, init_delay=0, timeout=180):
                raise TimeoutError("Device HTTPS service not ready after IP change.")
            self.init_session()


    def ping_device(self, ip=None, timeout=30):
        if not ip:
            ip = self.ip_address

        ip = ip.split("/")[0]

        system_type = platform.system().lower()
        if system_type.startswith("win"):
            ping_cmd = ["ping", "-n", "1", "-w", "1000", ip]
        else:
            ping_cmd = ["ping", "-c", "1", "-W", "1", ip]
    
        end_time = time.time() + timeout
        while time.time() < end_time:
            result = subprocess.run(
                ping_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if result.returncode == 0:
                return True
            time.sleep(1)
        return False


    def get_running_config(self):
        """Get existing configuration file from device."""
        if not self.session:
            self.init_session()

        if not self.session:
            raise Exception()

        config = {}
        for endpoint in RUNNING_CONFIG_ENDPOINTS:
            config_resp = self.session.get(f"https://{self.ip_address}/api/v1.0{endpoint}", verify=False, headers=self.headers)
    
            if not config_resp.ok:
                self.logger.error(config_resp.status_code)
                raise ConnectionError("Failed to get config.")

            config[endpoint] = config_resp.json()

        return config

    def get_standard_config(self, full_config=False):
        ip_cidr = self.config_ip_cidr if hasattr(self, "config_ip_cidr") and self.config_ip_cidr else None

        if ip_cidr:
            if self.gateway is None:
                running_config = self.get_running_config()
                gateway = running_config["/system/airos/configuration"]["network"]["interfaces"]["data"]["ipv4"]["defaultGateway"]
                self.logger.debug(f"Read gateway from device: {gateway}")
            else:
                gateway = self.gateway
        else:
            running_config = self.get_running_config()
            gateway = running_config["/system/airos/configuration"]["network"]["interfaces"]["data"]["ipv4"]["defaultGateway"]
            ip_cidr = running_config["/system/airos/configuration"]["network"]["interfaces"]["data"]["ipv4"]["cidr"]
            self.logger.debug(f"Read gateway from device: {gateway}")

        try:
            path = Path(self.full_config if full_config else self.base_config)
            directory = path.parent
            filename = path.name

            env = Environment(loader=FileSystemLoader(directory))
            env.trim_blocks = True
            env.lstrip_blocks = True
            template = env.get_template(filename)

            if full_config:
                params = {
                    "snmp_cstring": os.getenv("SNMP_COMMUNITY"),
                    "new_address_cidr": ip_cidr,
                    "new_address_gateway": gateway,
                    "mgmtvlan": MGMT_VLAN,
                    "azimuth": self.azimuth,
                    "number": self.device_number,
                    "height": self.height,
                    "ch_width": self.bandwidth,
                    "freq": self.frequency,
                    "tx_pwr": self.power_eirp,
                    "sitename": self.site_name,
                    "identifier": self.device_type["identifier"],
                    "antenna": self.antenna["name"],
                }
            else:
                params = {
                    "snmp_cstring": os.getenv("SNMP_COMMUNITY"),
                    "new_address_cidr": ip_cidr,
                    "new_address_gateway": gateway,
                    "mgmtvlan": MGMT_VLAN,
                    "azimuth": self.azimuth,
                    "number": self.device_number,
                    "height": self.height,
                    "ch_width": self.bandwidth,
                    "freq": self.frequency,
                    "tx_pwr": self.power_eirp,
                    "orig_ap_username": self.login["username"],
                    "orig_ap_password": self.login["password"],
                    "new_ap_username": LOGINS["AP"][0]["username"],
                    "new_ap_password": LOGINS["AP"][0]["password"],
                    "sitename": self.site_name,
                    "identifier": self.device_type["identifier"],
                    "antenna": self.antenna["name"],
                    "readonly": self.readonly
                }

            config = template.render(params)
            return json.loads(config)
        except Exception as err:
            raise SystemError(f"Failed to read base config file. {err}") from err

    def get_params(self):
        if not self.session:
            self.init_session()
        if not self.session:
            raise Exception()
        stat_resp = self.session.get(f"https://{self.ip_address}/api/v1.0/statistics", verify=False, headers=self.headers)
        if not stat_resp.ok:
            self.logger.error(stat_resp.status_code)
            raise ConnectionError("Failed to get config.")
        return stat_resp.json()

    def pre_check(self):
        result = []

        if not self.session:
            self.init_session()

        if not self.session:
            raise Exception()


        headers = {
                **self.headers,
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive"
                }

        device_status_resp = self.session.get(f"https://{self.ip_address}/api/v1.0/device", verify=False, headers=headers)
        if not device_status_resp.ok:
            raise ConnectionError("Failed to get device status.")

        device_status = device_status_resp.json()

        self.logger.debug(device_status_resp.content)

        try:

            # Firmware version
            result.append([
                "Firmware Version",
                device_status["identification"]["firmwareVersion"],
                self.device_type["firmware_standard"],
                (
                    device_status["identification"]["firmwareVersion"] == self.device_type["firmware_standard"]
                ),
            ])

            # Device Model
            result.append([
                "Device Model",
                self.device_type["model"],
                device_status["identification"]["model"],
                (
                    device_status["identification"]["model"] == self.device_type["model"]
                ),
            ])
    
        except KeyError as err:
            raise ConnectionError(f"Failed to get parameter from device: {err}")

        return result

    def update_firmware(self):
        if self.readonly:
            raise Exception("Attempted to update device firmware in readonly mode.")
        self.session = None
        self.headers = {}
        self.init_session()
        with open(self.firmware, "rb") as f:
            files = {"file": (Path(self.firmware).name, f, "application/octet-stream")}
            upload_resp = self.session.post(
                f"https://{self.ip_address}/api/v1.0/system/upgrade/direct",
                files=files, headers=self.headers, verify=False)
            if upload_resp.status_code in (401, 403):
                self.init_session()
                upload_resp = self.session.post(
                    f"https://{self.ip_address}/api/v1.0/system/upgrade/direct",
                    files=files, headers=self.headers, verify=False)
            if not upload_resp.ok:
                raise ConnectionError(f"Failed to upload firmware with status code {upload_resp.status_code}")
            time_start = time.monotonic()
            status = None
            percent = -1
            while time.monotonic() - time_start < UPGRADE_TIMEOUT:
                upgrade_resp = self.session.get(f"https://{self.ip_address}/api/v1.0/system/upgrade", headers=self.headers, verify=False)
                self.logger.debug(upgrade_resp.content)
                if not upgrade_resp.ok:
                    raise ConnectionError("Failed to upgrade firmware.")
                status = upgrade_resp.json()["status"]
                new_percent = upgrade_resp.json().get("progressPercent", percent)
                if new_percent != percent:
                    self.logger.info(f"Upgrade status: {new_percent}%")
                    percent = new_percent
                if status != "in_progress":
                    break
                time.sleep(2)
            if status != "finished":
                raise ConnectionError("Failed to upgrade firmware.")
        self.logger.info("Rebooting...")
        self.session.post(f"https://{self.ip_address}/api/v1.0/system/reboot", verify=False, headers=self.headers, data={"timeout":0})
        if not self.wait_until_ping(self.ip_address, init_delay=10, timeout=REBOOT_TIMEOUT):
            raise TimeoutError("Device did not answer ping after reboot.")
        if not self.wait_until_port_open(self.ip_address, port=443, init_delay=0, timeout=REBOOT_TIMEOUT):
            raise TimeoutError("Device HTTPS service not ready after reboot.")
        self.session = None
        self.headers = {}
        self.init_session()
        self.logger.info("Upgrade finished.")

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

    def wait_until_ping(self, ip=None, init_delay=10, timeout=300):
        ip = (ip or self.ip_address or "").split("/")[0]
        time.sleep(init_delay) 
        system_type = platform.system().lower()
        ping_cmd = ["ping", "-n", "1", "-w", "1000", ip] if system_type.startswith("win") \
                   else ["ping", "-c", "1", "-W", "1", ip]
        end = time.time() + timeout
        while time.time() < end:
            if subprocess.run(ping_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                return True
            time.sleep(1)
        return False

    @staticmethod
    def get_device_info(ip_address, device_type, password=None, run_tests=False):
        result = {}

        if device_type == "WAP":
            device_type = "Wave-AP"

        if device_type == "WAPM":
            device_type = "Wave-AP-Micro"

        params = {
            "ip_address": ip_address,
            "device_type": device_type,
        }

        d = None

        ap_type = get_item(device_type, DEVICE_TYPES)

        if password:
            params["password"] = password

        try:
            d = WaveConfig(**params, readonly=True)
            d.init_session()

            running_config = parsepath(d.get_running_config())

            standard_config = d.get_standard_config()

            standard_config = parsepath(dict(
                (c["route"], c["body"]) for c in standard_config.get("requests")
                ))

            # Convert JSON paths to lines of text
            result["standard_config"] = (
                "\n".join(
                    sorted([
                        f"{line['path']}: {line['value']}"
                        for line in standard_config
                    ])
                )
                .replace("False", "false")
                .replace("True", "true")
                .replace("None", "null")
            ) + "\n"

            result["running_config"] = (
                "\n".join(
                    sorted([
                        f"{line['path']}: {line['value']}"
                        for line in running_config
                    ])
                )
                .replace("False", "false")
                .replace("True", "true")
                .replace("None", "null")
            ) + "\n"
            if run_tests:
                result["test_results"] = [
                    {"name": x[0], "expected": x[2], "actual": x[1], "pass": x[3]}
                    for x in d.pre_check()
                ]

            params = d.get_params()

            d.logout()

            gps = params[0]["device"].get("gps")

            result["gps_latitude"] = gps.get("lat")
            result["gps_longitude"] = gps.get("lon")

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
