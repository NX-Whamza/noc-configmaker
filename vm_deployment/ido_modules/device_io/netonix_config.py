#!/usr/bin/python3

import io
import json
import os
import pprint
import re
from time import sleep
import time
from .util import *
from paramiko import SSHClient
import paramiko
from scp import SCPClient
import sys
import requests
from .update_nx_swt import update_nx_swt
import logging

DEBUG = True

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"
#DEFAULT_PASSWORD = os.getenv("SWT_STANDARD_PW")

TIMEOUT = 10


PRE_CHECK_ATTRIBUTES = [
    # (Human readable name, command, key name, expected value)
    ("Firmware version", "cat /www/version.txt", "", "1.5.25"),
    (
        "Device name",
        "awk -F'\"' '/Switch_Name/ {print $4}' /www/config.json",
        "",
        None
    ),
]

# (Switch name, Model code, port count, first AP port)
SWITCH_TYPES = [
    ("SWT-NXWS12", "NXWS12", 14, 5),
    ("SWT-NXWS14", "NXWS14", 14, 5),
    ("SWT-NXWS24", "NXWS24", 26, 7),
    ("SWT-NXWS26", "NXWS26", 26, 7),
]

AP_VOLTAGES = ["24V", "48V", "Off"]
AP_DEFAULT_VOLTAGE = "48V"

HELP_MESSAGE = (
    "Usage: %s [-a ap_count] [-c latitude,longitude] [-d device_number]\n\
                     [-i ip_address] [-n site-name] [-v voltage]\n\
                \n\
            Available options:\n\
                -a,--ap-count       Number of AP ports to configure switch to use\n\
                -c,--coordinates    Latitude & longitude of cabinet (comma-separated)\n\
                -d,--device-number  Switch identification number (increment for multiple); 1-2 digits\n\
                -i,--ip-address     IP address of switch to configure\n\
                -n,--site-name      Name of tower site, in format AA-BBBBBB-CC-##\n\
                -v,--ap-voltage     Voltage of AP PoE (%s)\n\
                -p,--password       Password to use when logging into device"
    % (__file__.split("/")[-1], ", ".join(AP_VOLTAGES))
)

BASE_PATH = os.getenv("BASE_CONFIG_PATH") + "/Netonix/"


class NetonixConfig:
    def __init__(self, logstream=None, **params):
        try:
            self.ssh = None
            self.scp = None
            self.ssh_channel = None
            self.params = params
            self.ip_address = params["ip_address"]
            self.subnet_mask = params.get("subnet_mask", "255.255.255.0")
            # self.gateway = params.get("gateway")
            self.username = params.get("username", DEFAULT_USERNAME)
            self.password = params.get("password", DEFAULT_PASSWORD)
            self.ap_count = params.get("ap_count", "6")
            self.latitude = params.get("latitude", "0")
            self.longitude = params.get("longitude", "0")
            self.device_number = params.get("device_number", "1")
            self.site_name = params.get("site_name")
            self.ap_voltage = params.get("ap_voltage", "48V")
            # self.role = params.get("role", "MAS")
            self.device_type = get_item(params.get("device_type"), SWITCH_TYPES)
            if self.ap_voltage not in AP_VOLTAGES:
                self.ap_voltage = AP_DEFAULT_VOLTAGE
            # Log callback
            self.on_log = params.get("on_log")
        except KeyError as err:
            raise ValueError("Missing required parameter: %s" % (err))

        self.logger = logging.getLogger(__name__ + f"_{self.ip_address}")
        self.logger.setLevel(
            logging.DEBUG if params.get("debug") or DEBUG else logging.INFO
        )

        if logstream:
            log_handler = logging.StreamHandler(logstream)
            log_handler.setFormatter(ConfigLogFormatter())
            log_handler.setLevel(logging.INFO)
            self.logger.addHandler(log_handler)

    def _init_ssh(self, username=None, password=None):
        self.ssh = SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        self.ssh.connect(
            self.ip_address,
            username=username or self.username,
            password=password or self.password,
        )

        self.ssh_channel = self.ssh.get_transport().open_session()
        self.ssh_channel.invoke_shell()

    def _init_scp(self, username=None, password=None):
        self._init_ssh(username=username, password=password)
        self.scp = SCPClient(self.ssh.get_transport())

    def send_ssh_command(self, command):
        try:
            if not self.ssh or not self.ssh_channel:
                self._init_ssh()
        except AttributeError:
            self._init_ssh()
        try:
            output = ""
            self.logger.debug(command)
            while not self.ssh_channel.send_ready():
                pass
            self.ssh_channel.sendall(command + "\n")
            # while not self.ssh_channel.exit_status_ready():
            #    pass

            sleep(0.7)

            # Print stdout if DEBUG
            # ('\n' and '\t' need to be replaced with newline and tab, respectively)
            while self.ssh_channel.recv_ready():
                output += (
                    self.ssh_channel.recv(4096)
                    .decode("ascii")
                    .replace("\\n", "\n")
                    .replace("\\t", "\t")
                )

            # while not re.match(r'^.*# ', "\n".join(output.split("\n")[-1])):

            self.logger.debug(output)
            return output

        except paramiko.SSHException as err:
            raise Exception(
                "Error while sending ssh command '%s': \n%s" % (command, err)
            )

    def _get_preset_values(self):
        try:
            if not self.ssh or not self.ssh_channel or not self.ssh_channel.active:
                self._init_ssh()
        except AttributeError as err:
            self._init_ssh()
        finally:
            output = self.send_ssh_command("cmdline")
            sleep(0.5)
            output += self.send_ssh_command("cat /www/config.json\n")

            start_time = time.perf_counter()
            while len(re.findall(r"^ ?}", output, flags=re.M)) < 1:
                if DEBUG:
                    print(
                        "\x1B[0GWaiting for preset config output%s [%.2f s]"
                        % (
                            "".join(
                                [
                                    "."
                                    for i in range(
                                        int(
                                            ((time.perf_counter() - start_time) * 2) % 4
                                        )
                                    )
                                ]
                            ).ljust(4),
                            time.perf_counter() - start_time,
                        ),
                        end="",
                    )
                # wait for entire output to be received
                if self.ssh_channel.recv_ready():
                    output += self.ssh_channel.recv(4096).decode("utf-8")
            if DEBUG:
                print()
            try:
                output = re.findall(r"\S?({.*^ ?})", output, flags=re.M | re.DOTALL)[0]

                # Match the contents of file
                preset = json.loads(output)
            except (TypeError, IndexError):
                raise Exception("Pre-existing config could not be loaded. ") from None
            return preset

    def _generate_config(self):
        base_name = self.device_type[1]
        if self.params.get("use_standard_vlans"):
            base_name = f"{base_name}_VLANS"
        path = BASE_PATH + base_name + ".json"
        with open(path, "r") as f:
            config = json.load(f)

        for i in range(int(self.ap_count)):
            config["Ports"][i + self.device_type[3] - 1]["Name"] = f"AP{i+1}"
            config["Ports"][i + self.device_type[3] - 1]["PoE"] = self.ap_voltage

        preset = self._get_preset_values()

        for i in range(len(preset.get("Ports"))):
            if preset.get("Ports")[i].get("Name") != "Port %s" % (
                preset.get("Ports")[i].get("Number")
            ):
                config["Ports"][i]["Name"] = preset.get("Ports")[i].get("Name")

        config["Switch_Name"] = (
            f"SWT-{self.device_type[1]}-{self.device_type[2]}-{self.device_number}.{self.site_name}"
        )
        config["GPS_Latitude"] = self.latitude
        config["GPS_Longitude"] = self.longitude
        config["Switch_Location"] = f"{self.site_name}"
        config["SNMP_Server_Location"] = f"{self.site_name}"
        config["MSTP_Name"] = f"{self.site_name.split('-', 1)[0]}-MSTP"
        config["IPv4_Address"] = self.ip_address
        config["IPv4_Netmask"] = (
            self.params.get("subnet_mask")
            or preset.get("IPv4_Netmask")
            or "255.255.255.0"
        )
        config["IPv4_Gateway"] = preset.get("IPv4_Gateway")

        return json.dumps(config, indent=3)

    def _upload_string_scp(self, remote_file, string):
        if not self.scp:
            raise Exception("SCP not initialized. ")

        file = io.BytesIO()
        file.write(string.encode("ascii"))
        file.seek(0)

        self.scp.putfo(file, remote_file)

    def _get_sfp_models(self):
        if not self.ssh or not self.ssh_channel:
            self._init_ssh()

        output = self.send_ssh_command("cmdline")
        sleep(0.5)
        output += self.send_ssh_command("cat /tmp/sfpstatus")

        # output might be printed on the same line as the command being sent
        re.sub(r"^.*?cmdline(.*)", r"\1", output, flags=re.M | re.DOTALL)

        self.logger.debug(output)

        timer_start = time.perf_counter()
        while (
            len(re.findall(r"^\d\d .*", output, flags=re.M)) < 2
            and time.perf_counter() < timer_start + TIMEOUT
        ):
            if self.ssh_channel.recv_ready:
                output += self.ssh_channel.recv(4096).decode("ascii")
        sfps = []
        for sfp in re.findall(r"^\d\d (.*)", output, flags=re.M):
            if "Empty" in sfp:
                continue
            sfps.append(tuple(sfp.split(" ")))

        return sfps

    def init_and_configure(self):
        precheck_result = self.pre_check()

        firmware_result = list(
            filter(lambda x: x[0] == "Firmware version", precheck_result)
        )

        if not firmware_result:
            self.logger.warning("Failed to check existing firmware version.")
        elif not firmware_result[0][3]:
            self.logger.info("Firmware out of date. Updating...")

            try:
                update_nx_swt(
                    self.ip_address,
                    username=self.username,
                    password=self.password,
                    on_log=self.on_log,
                )
            except requests.exceptions.SSLError:
                self.logger.error(
                    "Failed to update firmware: existing firmware is too old (TLS version). Update the switch manually, then try again.",
                )
                return

        self.logger.debug(self.params)
        if not self.scp or not self.ssh:
            self._init_scp(self.username, self.password)
        self.logger.info("Uploading configuration...")
        self._upload_string_scp("/www/config.json", self._generate_config())
        self.send_ssh_command("exit")
        self.logger.info("Configuration uploaded.")
        sleep(1.5)
        if self.password != DEFAULT_PASSWORD:
            # Set password to default if not already
            self.logger.info("Resetting password...")
            self.send_ssh_command("configure")
            sleep(0.5)
            self.send_ssh_command("credentials password %s" % DEFAULT_PASSWORD)
            output = self.send_ssh_command("exit\n\n")
            sleep(0.5)
            self.logger.info("Password reset.")
            output += self.send_ssh_command("\n\n")
            while (
                len(re.findall(r"^\S*# ", output, flags=re.M)) < 1
            ):  # wait for command to return
                output += self.ssh_channel.recv(4096).decode("utf-8")
                self.logger.debug(output)
                pass
        self.logger.info("Applying changes...")
        self.send_ssh_command("cmdline")
        self.logger.info("Changes applied. Rebooting.")
        self.send_ssh_command("php-cli config.php --apply")  # apply config
        self.send_ssh_command("reboot")
        self.ssh.close()

    @staticmethod
    def request_params(default_params={}, **params):
        if params.get("ip_address") is None:
            params["ip_address"] = input_default(
                "[?] IP Address: ",
                increment_ip_address(default_params.get("ip_address")),
            )
        if "/" in params.get("ip_address"):
            params["ip_address"], cidr = params["ip_address"].split("/")
            params["subnet_mask"] = calc_netmask(int(cidr))

        # params["gateway"] = params.get("gateway") or input_default(
        #    "[?] Gateway: ", default_params.get("gateway") or get_first_address(
        #        # Suggest default gateway of first address in range
        #        params.get("ip_address"), params.get(
        #            "subnet_mask", "255.255.255.0")
        #    )
        # )

        params["site_name"] = params.get("site_name") or input(
            "[?] Site name (ex. TX-PEASTR-NE-1): "
        )
        params["device_type"] = params.get("device_type") or prompt_list(
            "Enter switch type: ", SWITCH_TYPES
        )
        # params["role"] = params.get("role") or input_default(
        #     "[?] Role: ",
        #     "MAS"
        # )
        params["latitude"] = params.get("latitude") or input("[?] Device latitude: ")
        params["longitude"] = params.get("longitude") or input("[?] Device longitude: ")
        params["device_number"] = params.get("device_number") or input_default(
            "[?] Device number: ", 1
        )
        params["ap_count"] = params.get("ap_count") or input_default(
            "[?] AP count: ", 6
        )
        params["ap_voltage"] = params.get("ap_voltage") or prompt_list(
            "Enter AP PoE voltage: ", AP_VOLTAGES, default=AP_DEFAULT_VOLTAGE
        )
        # params["device_type"] = get_item(params.get("device_type") or
        #                                      prompt_list(
        #    "Enter switch model: ", SWITCH_TYPES), SWITCH_TYPES)

        params["name"] = "SWT-%s-%s-%s.%s" % (
            params.get("device_type")[1],
            params.get("device_type")[2],
            params.get("device_number"),
            params.get("site_name"),
        )

        return params

    def pre_check(self):
        attributes = []
        if not self.ssh:
            self._init_ssh()

        port_status = self.send_ssh_command("show interface status")
        while not port_status:
            while self.ssh_channel.recv_ready():
                port_status += self.ssh_channel.recv(4096).decode("utf-8")
        if len(port_status.split("\n")) > 2:

            for line in port_status.split("\n"):
                # Match PoE ports
                if match := re.match(
                    r"^(\d{1,2}) *\t(.*\S) *\t(.*\S) *\t(.*\S) *\t(.*\S)$", line
                ):
                    # Set attribute name to indicator for link & PoE status
                    number = match.group(1)
                    link = match.group(2)
                    poe_status = match.group(3)
                    poe_power = match.group(4)
                    name = match.group(5)

                    attributes.append(
                        (
                            f"Port {number} ({name})".ljust(3),
                            # Remove surrounding text
                            f"Ethernet - Link status: {link}, PoE: {poe_status} ({poe_power} W)",
                            None,
                            None,
                        )
                    )
                elif match := re.match(
                    r"^(\d{1,2}) *\t(.*\S) *\t *\t *\t(.*\S)$", line
                ):
                    number = match.group(1)
                    link = match.group(2)
                    name = match.group(3)

                    attributes.append(
                        (
                            f"Port {number} ({name})".ljust(3),
                            # Remove surrounding text
                            f"SFP - Link status: {link}",
                            None,
                            None,
                        )
                    )

        self.send_ssh_command("cmdline")
        sleep(0.2)

        for attribute in PRE_CHECK_ATTRIBUTES:
            output = self.send_ssh_command(attribute[1])

            if output.strip() == "":
                raise RuntimeError(f"pre_check: empty output for {attribute[1]!r}")

            try:
                if attribute[2] == "" or not attribute[2]:
                    result = output.split("\n")[0]
                else:
                    result = output.split(attribute[2])[1].split("\n")[0]
            except IndexError:
                attributes.append((attribute[0], None, attribute[3], False))
                break

            attributes.append(
                (
                    attribute[0],
                    result,
                    attribute[3],
                    attribute[3] in result if attribute[3] else None,
                )
            )

        return attributes

    @staticmethod
    def get_device_info(ip_address, device_type, password=None, run_tests=False):
        result = {}

        params = {
            "ip_address": ip_address,
            "device_type": device_type,
        }

        if password:
            params["password"] = password

        try:
            d = NetonixConfig(**params)
            if run_tests:
                result["test_results"] = [
                    {"name": x[0], "expected": x[2], "actual": x[1], "pass": x[3]}
                    for x in d.pre_check()
                ]
            d.ssh.close()

            result["success"] = True
        except Exception as err:
            result["success"] = False
            result["message"] = err

        return result


def main():
    # Command-line argument parsing
    #   Accepts either an array of strings or a string
    def parse_CLI_args(args, delimiter=" "):
        # Split args into array if string
        if isinstance(type, str):
            args = args.split(delimiter)

        result = {}
        while len(args) > 0:
            if "-" not in args[0]:
                args.pop(0)
            else:
                val = args[0].split("=")[0]
                if val == "--ip-address" or val == "-i":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["ip_address"] = args[0]
                elif val == "--site-name" or val == "-n":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["site_name"] = args[0]
                elif val == "--device-number" or val == "-d":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["device_number"] = args[0]
                elif val == "--ap-count" or val == "-a":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["ap_count"] = args[0]
                elif val == "--ap-voltage" or val == "-v":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["ap_voltage"] = get_item(args[0], AP_VOLTAGES)
                elif val == "--coordinates" or val == "-c":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["latitude"], result["longitude"] = args[0].split(",")
                elif val == "--password" or val == "-p":
                    if "=" not in args[0]:
                        args.pop(0)
                    else:
                        args[0] = args[0].split("=")[1]
                    result["password"] = args[0]
                elif val == "-h" or val == "--help":
                    print(HELP_MESSAGE)
                    exit()
                else:
                    print("Unrecognized option `%s`\n" % (args[0]))
                    print(HELP_MESSAGE)
                    exit()
                args.pop(0)
        return result

    try:
        netonix = NetonixConfig(
            **NetonixConfig.request_params(**parse_CLI_args(sys.argv))
        )
        netonix.init_and_configure()
    # except Exception as err:
    #    print("\n[!] %s\n\nExiting." % (err))
    except KeyboardInterrupt:
        sys.exit()


if __name__ == "__main__":
    main()
