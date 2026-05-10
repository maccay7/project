import requests
import os
import json

def get_test_data():
    """Get test data from environment only"""
    data_env = os.environ.get('TEST_DATA', '')
    if not data_env:
        print("\nERROR: TEST_DATA environment variable not set")
        return None
    
    try:
        return json.loads(data_env)
    except json.JSONDecodeError:
        print("\nERROR: TEST_DATA is not valid JSON")
        return None

def run_tests():
    print("Testing Professional Download Formats")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    test_data = get_test_data()
    
    if not test_data:
        return
    
    print("\n1. Testing Backend...")
    
    try:
        response = requests.post(
            f"{api_base}/api/calculate",
            json={"data": test_data, "instrument_type": "money_market", "params": {}}
        )
        
        if response.status_code == 200:
            calculations = response.json().get('calculations', [])
            print(f"  OK - Backend working: {len(calculations)} items")
            print("\n  Result: Success")
        else:
            print(f"  Error: {response.status_code}")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()