import requests
import os
import json

def run_tests():
    print("Testing Backend APIs")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    test_data_json = os.environ.get('TEST_DATA', '')
    
    # Test yield curve API (no data needed)
    print("\n1. Testing Yield Curve API...")
    try:
        response = requests.get(f"{api_base}/api/fred-yield-curve")
        
        if response.status_code == 200:
            data = response.json()
            rates = data.get('data', {}).get('current', [])
            print(f"  OK - {len(rates)} rates available")
        else:
            print(f"  Error: {response.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test calculations API (needs data)
    print("\n2. Testing Calculations API...")
    
    if not test_data_json:
        print("  SKIP - No TEST_DATA provided")
        print("\n" + "=" * 40)
        print("Test Complete")
        return
    
    try:
        test_data = json.loads(test_data_json)
    except json.JSONDecodeError:
        print("  ERROR: TEST_DATA is not valid JSON")
        return
    
    try:
        response = requests.post(
            f"{api_base}/api/calculate",
            json={"data": test_data, "instrument_type": "money_market", "params": {}}
        )
        
        if response.status_code == 200:
            calcs = response.json().get('calculations', [])
            print(f"  OK - {len(calcs)} calculations")
        else:
            print(f"  Error: {response.status_code}")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()