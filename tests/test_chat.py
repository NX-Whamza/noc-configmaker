#!/usr/bin/env python3
import requests
import json

def test_chat():
    url = "http://127.0.0.1:5000/api/chat"
    data = {"message": "What do you know about MikroTik RouterOS?"}
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        if result.get('success'):
            print("✅ Chat Response:")
            print(result.get('reply', 'No reply'))
        else:
            print("❌ Error:", result.get('error'))
            
    except Exception as e:
        print("❌ Request failed:", str(e))

if __name__ == "__main__":
    test_chat()
