import requests
import os
import json

def run_tests():
    print("Testing Calculations Workflow")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    test_data_json = os.environ.get('TEST_DATA', '')
    
    if not test_data_json:
        print("\nERROR: TEST_DATA environment variable not set")
        return
    
    try:
        test_data = json.loads(test_data_json)
    except json.JSONDecodeError:
        print("\nERROR: TEST_DATA is not valid JSON")
        return
    
    calc_url = f"{api_base}/api/calculate"
    
    print(f"\nTesting {len(test_data)} records...")
    
    try:
        response = requests.post(
            calc_url,
            json={"data": test_data, "instrument_type": "treasury_bills", "params": {}}
        )
        
        if response.status_code == 200:
            result = response.json()
            calculations = result.get('data', result.get('calculations', []))
            print(f"  OK - {len(calculations)} calculations")
            
            # Show first result sample
            if calculations:
                first = calculations[0]
                print("\n  Sample calculation:")
                for key, value in list(first.items())[:4]:
                    print(f"    {key}: {value}")
        else:
            print(f"  Error: {response.status_code}")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()