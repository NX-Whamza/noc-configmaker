import os
import re
import json
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


MIKROTIK_URLS = [
    # Core landing and v7 docs that are stable and not huge
    "https://help.mikrotik.com/docs/display/ROS/RouterOS",
    "https://help.mikrotik.com/docs/display/ROS/RouterOS+v7",
    "https://help.mikrotik.com/docs/display/ROS/OSPF",
    "https://help.mikrotik.com/docs/display/ROS/BGP",
    "https://help.mikrotik.com/docs/display/ROS/Bridge",
    "https://help.mikrotik.com/docs/display/ROS/Firewall",
    "https://help.mikrotik.com/docs/display/ROS/DHCP+Server",
    "https://help.mikrotik.com/docs/display/ROS/IP+Addresses",
    "https://help.mikrotik.com/docs/display/ROS/NTP+client",
    "https://help.mikrotik.com/docs/display/ROS/DNS",
]


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name.strip("._") or "doc"


def extract_readable_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Remove scripts/styles/navs
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    # Heuristic: keep main content area if present
    main = soup.find(id=re.compile("content|main", re.I)) or soup
    text = main.get_text("\n", strip=True)
    return text


def fetch_and_save(url: str, out_dir: str) -> dict:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    text = extract_readable_text(resp.text)
    parsed = urlparse(url)
    fname = sanitize_filename((parsed.path or "").replace("/docs/display/ROS/", "") or parsed.netloc)
    path = os.path.join(out_dir, f"mikrotik_{fname or 'doc'}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Source: {url}\n\n")
        f.write(text)
    return {"url": url, "file": path, "bytes": len(text.encode("utf-8"))}


def main():
    training_dir = os.environ.get("ROS_TRAINING_DIR") or os.path.join(os.getcwd(), "ros-migration-trainer-v3")
    if not os.path.isdir(training_dir):
        os.makedirs(training_dir, exist_ok=True)

    summary = {"saved": []}
    for url in MIKROTIK_URLS:
        try:
            info = fetch_and_save(url, training_dir)
            summary["saved"].append(info)
            time.sleep(0.5)
        except Exception as e:
            summary["saved"].append({"url": url, "error": str(e)})

    index_path = os.path.join(training_dir, "mikrotik_docs_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps({"training_dir": training_dir, **summary}, indent=2))


if __name__ == "__main__":
    main()


