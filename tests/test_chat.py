#!/usr/bin/env python3
from __future__ import annotations

import requests


def test_chat() -> None:
    url = "http://127.0.0.1:5000/api/chat"
    data = {"message": "What do you know about MikroTik RouterOS?"}

    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            print("[OK] Chat Response:")
            print(result.get("reply", "No reply"))
        else:
            print("[ERROR] Error:", result.get("error"))
    except Exception as e:
        print("[ERROR] Request failed:", str(e))


if __name__ == "__main__":
    test_chat()

