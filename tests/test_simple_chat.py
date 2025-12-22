#!/usr/bin/env python3
from __future__ import annotations

import requests


def test_simple_chat() -> None:
    url = "http://127.0.0.1:5000/api/chat"
    data = {"message": "Hello, are you working?"}

    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            reply = result.get("reply", "No reply")
            print("[OK] Backend chat endpoint responded")
            print("Response:", (reply[:100] + "...") if len(reply) > 100 else reply)
        else:
            print("[ERROR] Error:", result.get("error"))
    except requests.exceptions.Timeout:
        print("[ERROR] Request timed out (model may be slow/unavailable)")
    except Exception as e:
        print("[ERROR] Request failed:", str(e))


if __name__ == "__main__":
    test_simple_chat()

