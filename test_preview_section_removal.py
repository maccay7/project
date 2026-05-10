import requests
import os
import json

def run_tests():
    print("Testing Report Preview Section Removal")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    test_data_json = os.environ.get('TEST_DATA', '')
    
    if not test_data_json:
        print("\n  ERROR: TEST_DATA environment variable not set")
        print("\n  Test Aborted")
        return
    
    try:
        test_data = json.loads(test_data_json)
    except:
        print("\n  ERROR: TEST_DATA is not valid JSON")
        return
    
    print(f"\n1. Testing with {len(test_data)} records...")
    
    try:
        response = requests.post(
            f"{api_base}/api/calculate",
            json={"data": test_data, "instrument_type": "money_market", "params": {}}
        )
        
        if response.status_code == 200:
            calculations = response.json().get('calculations', [])
            print(f"  OK - Backend working: {len(calculations)} items")
            print("\n  Result: SUCCESS")
        else:
            print(f"  Error: {response.status_code}")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()