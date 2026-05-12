import requests
import os
import json

def run_tests():
    print("Frontend Display Test")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    test_data = os.environ.get('TEST_DATA', '')
    
    # Test calculations API
    print("\n1. Testing Calculations API...")
    try:
        if test_data:
            data = json.loads(test_data)
            resp = requests.post(f"{api_base}/api/calculate", 
                json={"data": data, "instrument_type": "money_market", "params": {}})
        else:
            resp = requests.options(f"{api_base}/api/calculate")
        
        print(f"  OK - API reachable" if resp.status_code < 500 else f"  Error: {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test yield curve API
    print("\n2. Testing Yield Curve API...")
    try:
        resp = requests.get(f"{api_base}/api/fred-yield-curve")
        if resp.status_code == 200:
            rates = resp.json().get('data', {}).get('current', [])
            print(f"  OK - {len(rates)} rates")
        else:
            print(f"  Error: {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n3. Data comes from frontend upload")
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()