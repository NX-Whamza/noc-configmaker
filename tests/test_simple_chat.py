#!/usr/bin/env python3
import requests
import json

def test_simple_chat():
    url = "http://127.0.0.1:5000/api/chat"
    data = {"message": "Hello, are you working?"}
    
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get('success'):
            print("✅ Backend is working!")
            print("Response:", result.get('reply', 'No reply')[:100] + "...")
        else:
            print("❌ Error:", result.get('error'))
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - model is too slow")
    except Exception as e:
        print("❌ Request failed:", str(e))

if __name__ == "__main__":
    test_simple_chat()
