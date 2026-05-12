import requests
import os

def run_tests():
    print("Testing Backend APIs")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    
    # Test 1: Yield Curve API
    print("\n1. Testing Yield Curve API...")
    try:
        resp = requests.get(f"{api_base}/api/fred-yield-curve")
        if resp.status_code == 200:
            rates = resp.json().get('data', {}).get('current', [])
            print(f"  OK - {len(rates)} rates")
        else:
            print(f"  Error: {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test 2: Calculations API
    print("\n2. Testing Calculations API...")
    test_data = os.environ.get('TEST_DATA', '')
    
    if not test_data:
        print("  SKIP - No data (data comes from frontend)")
    else:
        try:
            resp = requests.post(
                f"{api_base}/api/calculate",
                json={"data": json.loads(test_data), "instrument_type": "money_market", "params": {}}
            )
            if resp.status_code == 200:
                calcs = resp.json().get('calculations', [])
                print(f"  OK - {len(calcs)} calculations")
            else:
                print(f"  Error: {resp.status_code}")
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    import json
    run_tests()