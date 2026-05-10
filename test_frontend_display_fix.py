import requests
import os
import json

def run_tests():
    print("Frontend Display Test")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    test_data_json = os.environ.get('TEST_DATA', '')
    
    # Test calculations API
    print("\n1. Testing Calculations API...")
    try:
        if test_data_json:
            test_data = json.loads(test_data_json)
            response = requests.post(
                f"{api_base}/api/calculate",
                json={"data": test_data, "instrument_type": "money_market", "params": {}}
            )
        else:
            # Just check if endpoint is reachable
            response = requests.options(f"{api_base}/api/calculate")
        
        if response.status_code < 500:
            print(f"  OK - Calculations API reachable")
        else:
            print(f"  Error: {response.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test yield curve API
    print("\n2. Testing Yield Curve API...")
    try:
        response = requests.get(f"{api_base}/api/fred-yield-curve")
        
        if response.status_code == 200:
            data = response.json().get('data', {})
            rates = data.get('current', [])
            print(f"  OK - {len(rates)} rates available")
        else:
            print(f"  Error: {response.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")
    print("\nNote: Upload data through frontend to see full results")

if __name__ == "__main__":
    run_tests()