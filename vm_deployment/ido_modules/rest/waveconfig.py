import os
import csv
import json
import threading
import time
import re
import requests
import urllib3
import paramiko
import platform
import subprocess
import ipaddress
from datetime import datetime

# from flask import Flask, request, jsonify, render_template
from typing import Annotated, Optional
from fastapi import FastAPI, Request, UploadFile, APIRouter, File, Form
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
import openpyxl
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

from device_io.wave_config import WaveConfig
from device_io.mac import normalize_mac


app = APIRouter()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG_TEMPLATE_PATH = os.getenv("BASE_CONFIG_PATH") + "/Ubiquiti/Wave/"
CONFIG_NAME = "config.json"

SMAP_KEY = os.getenv("SMAP_KEY")

with open(os.getenv("BNG_SSH_SERVER_CONFIG"), "r") as f:
    SSH_SERVERS = json.load(f)

AP_ORIG_USER = ["ubnt", "admin"]
AP_ORIG_PASS = ["ubnt", os.getenv("WAVE_AP_PASS")]
AP_NEW_USER = "admin"
AP_NEW_PASS = os.getenv("WAVE_AP_PASS")

MGMT_VLAN = 3000

BNG_IP_CACHE = {}
BNG_CACHE_LOCK = threading.Lock()

jobs = {}
lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=int(os.getenv("WAVECONFIG_MAX_WORKERS", "16")))

KEY_MAP = {
    "AP MAC": "AP MAC", "MAC": "AP MAC", "APMAC": "AP MAC",
    "SITE NAME": "SITENAME", "SITENAME": "SITENAME", "NAME": "SITENAME",
    "IP (CIDR)": "IP (CIDR)", "IP/CIDR": "IP (CIDR)", "IP / CIDR": "IP (CIDR)", "IP": "IP (CIDR)",
    "GATEWAY": "GATEWAY", "GW": "GATEWAY",
    "AZIMUTH": "AZIMUTH", "BEARING": "AZIMUTH",
    "NUMBER": "NUMBER", "#": "NUMBER",
    "HEIGHT": "HEIGHT",
    "MODEL": "MODEL", "DEVICE": "MODEL", "RADIO MODEL": "MODEL"
}

REQUIRED_MIN_COLS = {"SITENAME", "IP (CIDR)", "GATEWAY", "AZIMUTH", "NUMBER", "HEIGHT", "MODEL"}

def canonicalize_key(k: str) -> str:
    return str(k or "").replace("\ufeff", "").strip().upper()

def normalize_row_keys(row: dict) -> dict:
    out = {}
    for k, v in (row or {}).items():
        ck = canonicalize_key(k)
        mapped = KEY_MAP.get(ck, ck)
        out[mapped] = (v or "").strip() if isinstance(v, str) else v
    ap_mac = normalize_mac(out.get("AP MAC"))
    return {
        "AP MAC": ap_mac,
        "SITENAME": str(out.get("SITENAME") or ""),
        "IP (CIDR)": str(out.get("IP (CIDR)") or ""),
        "GATEWAY": str(out.get("GATEWAY") or ""),
        "AZIMUTH": str(out.get("AZIMUTH") or "0"),
        "NUMBER": str(out.get("NUMBER") or "1"),
        "HEIGHT": str(out.get("HEIGHT") or ""),
        "MODEL": str(out.get("MODEL") or "Wave-AP")
    }

def ip_without_cidr(ip_cidr):
    return ip_cidr.split("/")[0].strip()


def ping_device(ip, timeout=30):
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

def _normalize_mac(mac):
    return normalize_mac(mac)

def _parse_ip_from_output(output):
    if not output:
        return None
    m = re.search(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s", output, re.MULTILINE)
    return m.group(1) if m else None

def warm_bng_ip_cache(mac_list):
    macs = {_normalize_mac(m) for m in mac_list if _normalize_mac(m)}
    if not macs:
        return
    print(f"[DEBUG] Starting BNG IP cache warm-up for {len(macs)} MACs")
    with BNG_CACHE_LOCK:
        remaining = {m for m in macs if m not in BNG_IP_CACHE}
    if not remaining:
        print("[DEBUG] All requested MACs already in cache; skipping BNG lookup.")
        return
    for server in SSH_SERVERS:
        if not remaining:
            break
        print(f"[DEBUG] Connecting to BNG server {server['hostname']} for {len(remaining)} unresolved MACs")
        ssh = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=server["hostname"],
                port=server["port"],
                username=server["username"],
                password=server["password"],
                timeout=10,
                look_for_keys=False,
                allow_agent=False,
            )
            chan = ssh.invoke_shell()
            time.sleep(0.5)
            try:
                _ = chan.recv(65535)
            except Exception:
                pass
            resolved_now = set()
            for mac in list(remaining):
                cmd = f"show service id 300 dhcp lease-state | match context all {mac}\n"
                print(f"[DEBUG] Running BNG lookup for {mac} on {server['hostname']}")
                try:
                    chan.send(cmd)
                    time.sleep(0.8)
                    out = b""
                    deadline = time.time() + 3
                    while time.time() < deadline:
                        if chan.recv_ready():
                            out += chan.recv(65535)
                            time.sleep(0.05)
                        else:
                            time.sleep(0.05)
                    text = out.decode("utf-8", errors="ignore")
                    ip = _parse_ip_from_output(text)
                    if ip:
                        print(f"[DEBUG] Found IP {ip} for MAC {mac} via {server['hostname']}")
                        with BNG_CACHE_LOCK:
                            BNG_IP_CACHE[mac] = ip.strip()
                        resolved_now.add(mac)
                    else:
                        print(f"[DEBUG] No IP found for {mac} on {server['hostname']}")
                except Exception as e:
                    print(f"[DEBUG] Shell error during lookup for {mac} on {server['hostname']}: {e}")
                time.sleep(0.05)
            remaining -= resolved_now
        except Exception as e:
            print(f"[DEBUG] SSH error on {server['hostname']}: {e}")
        finally:
            try:
                if ssh:
                    ssh.close()
            except Exception:
                pass
    if remaining:
        print(f"[DEBUG] Falling back to API lookup for {len(remaining)} unresolved MACs")
        for mac in list(remaining):
            try:
                api_url = "http://smap-db-dev.nxlink.com/API/get_ip_mac_current"
                headers = {"Authorization": SMAP_KEY, "Content-Type": "application/json"}
                payload = {"query": mac.upper()}
                print(f"[DEBUG] API lookup for MAC {mac}")
                resp = requests.post(api_url, headers=headers, json=payload, timeout=5)
                print(f"[DEBUG] API status code for {mac}: {resp.status_code}")
                if resp.ok:
                    data = resp.json()
                    print(f"[DEBUG] API response for {mac}: {data}")
                    if "get_ip_mac_current" in data and len(data["get_ip_mac_current"]) > 0:
                        ip = data["get_ip_mac_current"][0].get("ip")
                        if ip:
                            print(f"[DEBUG] Found IP {ip} for {mac} via API")
                            with BNG_CACHE_LOCK:
                                BNG_IP_CACHE[mac] = str(ip).strip()
                            remaining.discard(mac)
                else:
                    print(f"[DEBUG] API non-OK for {mac}: {resp.text}")
            except Exception as e:
                print(f"[DEBUG] API error for {mac}: {e}")
    print(f"[DEBUG] BNG warm-up complete. Cached {len(BNG_IP_CACHE)} total entries.")


def get_current_ip(mac_address):
    mac = _normalize_mac(mac_address)
    if not mac:
        return None
    with BNG_CACHE_LOCK:
        if mac in BNG_IP_CACHE:
            print(f"[DEBUG] Cache hit for MAC {mac}: {BNG_IP_CACHE[mac]}")
            return BNG_IP_CACHE[mac]
    print(f"[DEBUG] Cache miss for MAC {mac}, warming...")
    warm_bng_ip_cache([mac])
    with BNG_CACHE_LOCK:
        ip = BNG_IP_CACHE.get(mac)
    if ip:
        print(f"[DEBUG] Returning cached IP {ip} for MAC {mac}")
    else:
        print(f"[DEBUG] No IP found for MAC {mac} after warm-up")
    return ip

def login(session, test_orig_address):
    for username in AP_ORIG_USER:
        for password in AP_ORIG_PASS:
            login_result = try_login_with_credentials(session, test_orig_address, username, password)

            if login_result:
                return {
                        "username": username,
                        "password": password,
                        "token": login_result
                        }

def try_login_with_credentials(session, test_orig_address, username, password):
    print(f"[DEBUG] Attempting login to {test_orig_address} as user {username}")
    url = f"https://{test_orig_address}/api/v1.0/user/login"
    payload = {"username": username, "password": password}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    try:
        response = session.post(
            url, headers=headers, json=payload, verify=False, timeout=30
        )
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Login request exception: {e}")
        return None

    print(f"[DEBUG] Login response code: {response.status_code}, text: {response.text}")
    if response.ok:
        token = response.headers.get("x-auth-token")
        print(f"[DEBUG] Got x-auth-token: {token}")
        return token
    else:
        print("[DEBUG] Login failed")
        return None


def get_standard_config(
    new_addr_cidr,
    new_addr_gateway,
    hostname,
    azimuth,
    number,
    height,
    ch_width,
    freq,
    tx_pwr,
    username,
    password,
):
    env = Environment(loader=FileSystemLoader(CONFIG_TEMPLATE_PATH))
    env.trim_blocks = True
    env.lstrip_blocks = True

    template = env.get_template(CONFIG_NAME)

    params = {
        "snmp_cstring": os.getenv("SNMP_COMMUNITY"),
        "new_address_cidr": new_addr_cidr,
        "new_address_gateway": new_addr_gateway,
        "mgmtvlan": MGMT_VLAN,
        "azimuth": azimuth,
        "number": number,
        "height": height,
        "ch_width": ch_width,
        "freq": freq,
        "tx_pwr": tx_pwr,
        "orig_ap_username": username,
        "orig_ap_password": password,
        "new_ap_username": AP_NEW_USER,
        "new_ap_password": AP_NEW_PASS,
        "sitename": hostname,
        "identifier": "WAP",
        "antenna": "UB030",
        "readonly": False
    }

    config = template.render(params)

    print(config)

    return config


def setup_radio(
    session,
    x_auth_token,
    test_orig_address,
    orig_username,
    orig_password,
    new_address_cidr,
    new_address_gateway,
    azimuth,
    number,
    height,
    hostname,
    ch_width,
    freq,
    tx_pwr,
):
    print(f"[DEBUG] Setting up radio on {test_orig_address}")
    url = f"https://{test_orig_address}/api/v1.0/tools/compose"
    payload = json.loads(
        get_standard_config(
            new_address_cidr,
            new_address_gateway,
            hostname,
            azimuth, 
            number,
            height,
            ch_width,
            freq,
            tx_pwr,
            orig_username,
            orig_password,
        )
    )
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-auth-token": x_auth_token,
    }

    print(f"[DEBUG] Sending configuration payload to {test_orig_address}")
    new_ip = ip_without_cidr(new_address_cidr)
    try:
        response = session.post(
            url, headers=headers, json=payload, verify=False, timeout=20
        )
        print(
            f"[DEBUG] Compose response code: {response.status_code}, text: {response.text}"
        )
    except requests.exceptions.Timeout:
        print(
            "[DEBUG] Timeout waiting for response from device, attempting ping new IP"
        )

        if new_ip != test_orig_address and ping_device(new_ip, timeout=30):
            print("[DEBUG] Ping success after timeout, assuming success")
            return True
        else:
            print("[DEBUG] Ping fail after timeout, returning fail")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] setup_radio request exception: {e}")
        return False

    if '"statusCode":400' in response.text:
        print("[DEBUG] statusCode 400 in response, returning False")
        return False
    elif response.ok and '"statusCode":400' not in response.text:
        print("[DEBUG] Response OK, checking ping on new IP")
        if ping_device(new_ip, timeout=10):
            print("[DEBUG] Ping success, returning True")
            return True
        else:
            print("[DEBUG] Ping fail after success response, returning True anyway")
            return True
    else:
        print("[DEBUG] Unexpected response, trying ping new IP")
        if ping_device(new_ip, timeout=10):
            print("[DEBUG] Ping success, returning True")
            return True
        else:
            print("[DEBUG] Ping fail, returning False")
            return False


def _map_error_status(e: Exception) -> str:
    s = str(e or "").lower()
    if "determine ip address for mac" in s:
        return "No IP found for MAC"
    if "unreachable" in s:
        return "Device Unreachable"
    if "configuration failed" in s:
        return "Configuration failed"
    return "Failed"


def _configure_one(job_id: str, idx: int, device: dict):
    def set_status(status=None, detail=None, error=None):
        with lock:
            if status is not None:
                jobs[job_id]["devices"][idx]["status"] = status
            if detail is not None:
                jobs[job_id]["devices"][idx]["detail"] = detail
            if error is not None:
                jobs[job_id]["devices"][idx]["error"] = error

    with lock:
        jobs[job_id]["devices"][idx].setdefault("detail", "")
        jobs[job_id]["devices"][idx].setdefault("error", "")

    set_status("Configuring", "Starting")

    mac_address = normalize_mac(device.get("AP MAC"))
    sitename = device["SITENAME"].strip()
    new_address_cidr = device["IP (CIDR)"].strip()
    new_address_gateway = device["GATEWAY"].strip()
    azimuth = str(int(device["AZIMUTH"].strip()) % 360).zfill(3)
    number = int(device["NUMBER"].strip())
    height = int(device["HEIGHT"].strip())
    model = device["MODEL"].strip()
    tx_pwr = 41 if model == "Wave-AP-Micro" else 39
    planned_ip = new_address_cidr.split("/")[0].strip()

    params_base = {
        "azimuth": azimuth,
        "site_name": sitename,
        "device_number": number,
        "height": height,
        "frequency": 5200,
        "bandwidth": 20,
        "power": tx_pwr,
        "ip_address": new_address_cidr,
        "gateway": new_address_gateway,
        "device_type": model,
    }

    def try_direct_static():
        set_status("Configuring", f"Direct to planned IP {planned_ip}")
        if not ping_device(planned_ip, timeout=5):
            set_status("Device Unreachable", "", f"Planned IP {planned_ip} did not answer ping")
            _maybe_mark_done(job_id)
            return
        try:
            d = WaveConfig(**dict(params_base, use_dhcp=False))
            d.configure_with_bank_check(lambda msg: set_status("Configuring", msg))
            set_status("Done", "", "")
        except Exception as e:
            set_status(_map_error_status(e), "", str(e))
        finally:
            _maybe_mark_done(job_id)

    try:
        if mac_address:
            set_status("Configuring", f"DHCP path for {mac_address.lower()}")
            try:
                d = WaveConfig(**dict(params_base, use_dhcp=True, mac_address=mac_address))
                d.configure_with_bank_check(lambda msg: set_status("Configuring", msg))
                set_status("Done", "", "")
                _maybe_mark_done(job_id)
                return
            except Exception as e:
                s = str(e or "").lower()
                if "determine ip address for mac" in s or "no ip found for mac" in s:
                    set_status("Configuring", "BNG lookup failed, trying planned IP")
                    try_direct_static()
                    return
                set_status(_map_error_status(e), "", str(e))
                _maybe_mark_done(job_id)
                return
        else:
            try_direct_static()
            return
    except Exception as e:
        set_status(_map_error_status(e), "", str(e))
        _maybe_mark_done(job_id)


def _maybe_mark_done(job_id: str):
    with lock:
        devs = jobs[job_id]["devices"]
        if all(d["status"] in ("Done", "Failed", "Device Unreachable", "No IP found for MAC", "Configuration failed") for d in devs):
            jobs[job_id]["done"] = True


# @app.get("/", response_class=HTMLResponse)
# async def index():
#     return render_template("index.html")


@app.post("/api/waveconfig/parse_csv")
async def parse_csv(csvfile: UploadFile = File(...)):
    if not csvfile:
        return JSONResponse(status_code=400, content={"error": "No file provided"})
    lines = csvfile.file.read().decode("utf-8", errors="ignore").splitlines()
    reader = csv.DictReader(lines)
    if not reader.fieldnames:
        return JSONResponse(status_code=400, content={"error": "Empty or invalid CSV"})
    normalized_headers = {KEY_MAP.get(canonicalize_key(h), canonicalize_key(h)) for h in reader.fieldnames}
    missing = REQUIRED_MIN_COLS - normalized_headers
    if missing:
        return JSONResponse(status_code=400, content={"error": "Missing required columns: " + ", ".join(sorted(missing))})
    rows = []
    for r in reader:
        rows.append(normalize_row_keys(r))
    return {"rows": rows}


@app.post("/api/waveconfig/parse_xlsx")
async def parse_xlsx(xlsxfile: UploadFile = File(...)):
    if not xlsxfile:
        return JSONResponse(status_code=400, content={"error": "No file provided"})
    if xlsxfile.content_type != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        return JSONResponse(status_code=400, content={"error": "Invalid file type. Please upload an XLSX file."})
    contents = await xlsxfile.read()
    try:
        wb = openpyxl.load_workbook(BytesIO(contents), read_only=True, data_only=True)
        rows = []
        configurator = wb['Configurator']
        form = wb['Tower Approval Form']

        sitename = str(configurator['B60'].value)
        gateway = str(configurator['Y64'].value)
        subnet = str(configurator['W64'].value)
        cidr = ipaddress.IPv4Network(f"0.0.0.0/{subnet}").prefixlen

        wave_ap_row = 64
        form_ap_row = 12

        idx = 0
        while configurator[f'A{wave_ap_row + idx}'].value != '' and isinstance(configurator[f'A{wave_ap_row + idx}'].value, int):
            row = idx + wave_ap_row
            azimuth = int(configurator[f'A{row}'].value)
            height = int(configurator[f'B{row}'].value)
            ip = str(configurator[f'Q{row}'].value)
            mac_cell = form[f'H{form_ap_row + idx}'].value
            mac = normalize_mac(mac_cell)
            number = 1
            model = "Wave-AP"
            rows.append({
                "AP MAC": mac,
                "SITENAME": sitename,
                "IP (CIDR)": f"{ip}/{cidr}",
                "GATEWAY": gateway,
                "AZIMUTH": azimuth,
                "NUMBER": number,
                "HEIGHT": height,
                "MODEL": model
            })
            idx += 1

        wave_count = idx
        wave_micro_row = wave_ap_row + wave_count
        while not isinstance(configurator[f"A{wave_micro_row}"].value, int):
            wave_micro_row += 1
            if wave_micro_row > 200:
                return JSONResponse(status_code=400, content={"error": "Failed to parse XLSX file."})

        idx = 0
        while configurator[f'A{wave_micro_row + idx}'].value != '' and isinstance(configurator[f'A{wave_micro_row + idx}'].value, int):
            row = idx + wave_micro_row
            azimuth = int(configurator[f'A{row}'].value)
            height = int(configurator[f'B{row}'].value)
            ip = str(configurator[f'Q{row}'].value)
            mac_cell = form[f'H{form_ap_row + wave_count + idx}'].value
            mac = normalize_mac(mac_cell)
            number = 1
            model = "Wave-AP-Micro"
            rows.append({
                "AP MAC": mac,
                "SITENAME": sitename,
                "IP (CIDR)": f"{ip}/{cidr}",
                "GATEWAY": gateway,
                "AZIMUTH": azimuth,
                "NUMBER": number,
                "HEIGHT": height,
                "MODEL": model
            })
            idx += 1
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Failed to parse XLSX file."})
    return {"rows": rows}

@app.post("/api/waveconfig/start")
async def start(
    mode: Annotated[str, Form()],
    devices: Annotated[str, Form()] = None,
    csvfile: UploadFile = None,
):
    if not devices:
        devices = []

    if mode == "csv":
        if not csvfile:
            return JSONResponse(status_code=400, content={"error": "No file provided"})
        file_data = (await csvfile.read()).decode("utf-8", errors="ignore").splitlines()
        reader = csv.DictReader(file_data)
        if not reader.fieldnames:
            return JSONResponse(status_code=400, content={"error": "Empty or invalid CSV"})
        normalized_headers = {KEY_MAP.get(canonicalize_key(h), canonicalize_key(h)) for h in reader.fieldnames}
        missing = REQUIRED_MIN_COLS - normalized_headers
        if missing:
            return JSONResponse(status_code=400, content={"error": "Missing required columns: " + ", ".join(sorted(missing))})
        parsed = []
        for row in reader:
            norm = normalize_row_keys(row)
            norm["status"] = "Preparing"
            norm["error"] = ""
            parsed.append(norm)
        devices = parsed
    else:
        if not devices:
            return JSONResponse(status_code=400, content={"error": "No device list provided"})
        arr = json.loads(devices)
        parsed = []
        for d in arr:
            n = normalize_row_keys(d)
            n["status"] = "Preparing"
            n["error"] = ""
            parsed.append(n)
        devices = parsed

    job_id = str(int(time.time()))
    with lock:
        jobs[job_id] = {"devices": devices, "done": False}

    for idx, device in enumerate(devices):
        executor.submit(_configure_one, job_id, idx, device)

    return {"job_id": job_id}

@app.get("/api/waveconfig/status/{job_id}")
async def status(job_id: str):
    with lock:
        if job_id not in jobs:
            return JSONResponse(status_code=404, content={"error": "Invalid job"})
        return jobs[job_id]

@app.post("/api/waveconfig/full_config")
async def get_full_config(device: Annotated[str, Form()]):
    device_parsed = json.loads(device)

    mac_address = normalize_mac(device_parsed.get("AP MAC", ""))
    sitename = device_parsed["SITENAME"].strip()
    new_address_cidr = device_parsed["IP (CIDR)"].strip()
    new_address_gateway = device_parsed["GATEWAY"].strip()
    azimuth = str(int(device_parsed["AZIMUTH"].strip()) % 360).zfill(3)
    number = int(device_parsed["NUMBER"].strip())
    height = int(device_parsed["HEIGHT"].strip())
    model = device_parsed["MODEL"].strip()

    tx_pwr = 41 if model == "Wave-AP-Micro" else 39

    params = {
        "azimuth": azimuth,
        "site_name": sitename,
        "device_number": number,
        "height": height,
        "frequency": 5200,
        "bandwidth": 20,
        "power": tx_pwr,
        "ip_address": new_address_cidr,
        "use_dhcp": len(mac_address) != 0,
        "mac_address": mac_address,
        "gateway": new_address_gateway,
        "device_type": model,
        "target_ip_address": new_address_cidr
    }

    d = WaveConfig(**params)
    return d.get_standard_config(full_config=True)


if __name__ == "__main__":
    f = FastAPI()
    f.include_router(app)
    # f.run(host="0.0.0.0", port=5000)
