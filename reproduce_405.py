import requests
import json
import time

def test_ftth_bng():
    # Local server address
    base_url = "http://localhost:5000"
    endpoint = "/api/generate-ftth-bng"
    url = f"{base_url}{endpoint}"
    
    print(f"--- Starting API Connectivity Test ---")
    print(f"Target URL: {url}")
    
    # 1. Test Health Check first
    try:
        health_resp = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"Health Check: {health_resp.status_code} - {health_resp.text[:50]}")
    except Exception as e:
        print(f"Health Check Failed: {e}")
        print("Is the server running on http://localhost:5000?")
        return

    # 2. Test OPTIONS request (CORS Preflight)
    print(f"\nTesting OPTIONS request...")
    try:
        opt_resp = requests.options(url, timeout=5)
        print(f"OPTIONS Response Status: {opt_resp.status_code}")
        print(f"Allow Header: {opt_resp.headers.get('Allow', 'Not Present')}")
        print(f"Access-Control-Allow-Methods: {opt_resp.headers.get('Access-Control-Allow-Methods', 'Not Present')}")
    except Exception as e:
        print(f"OPTIONS Request Failed: {e}")

    # 3. Test POST request with sample data
    print(f"\nTesting POST request...")
    sample_data = {
        "deployment_type": "instate",
        "site_name": "TEST-LAB",
        "router_identity": "RTR-MT2216-AR1.TEST-LAB-FTTH-BNG",
        "location": "32.9,-97.5",
        "loopback_ip": "10.0.0.1/32",
        "cpe_network": "10.1.0.0/22",
        "cgnat_private": "100.64.0.0/22",
        "cgnat_public": "1.1.1.1/32",
        "unauth_network": "10.2.0.0/22",
        "olt_network": "10.3.0.0/29",
        "uplink_port": "sfp28-1",
        "uplink_type": "routed",
        "uplink_ip": "10.255.255.1/30",
        "uplink_speed": "auto",
        "uplink_comment": "to-CORE",
        "uplink_cost": "10",
        "olt_ports": [
            {"port": "sfp28-3", "speed": "10G-baseSR-LR", "comment": "OLT-1"},
            {"port": "sfp28-4", "speed": "10G-baseSR-LR", "comment": "OLT-2"}
        ]
    }
    
    try:
        post_resp = requests.post(url, json=sample_data, timeout=10)
        print(f"POST Response Status: {post_resp.status_code}")
        
        if post_resp.status_code == 200:
            result = post_resp.json()
            if result.get('success'):
                config_len = len(result.get('config', ''))
                print(f"✅ Success! Generated config length: {config_len}")
            else:
                print(f"❌ API Error: {result.get('error')}")
        elif post_resp.status_code == 405:
            print(f"❌ 405 Method Not Allowed. This is the issue we're tracking.")
            print(f"Response Body: {post_resp.text[:200]}")
        else:
            print(f"❌ Received Status {post_resp.status_code}")
            print(f"Response Body: {post_resp.text[:200]}")
            
    except Exception as e:
        print(f"POST Request Failed: {e}")

if __name__ == "__main__":
    test_ftth_bng()
