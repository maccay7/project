import requests
import os
import json

def run_tests():
    print("Testing API Response Parsing")
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
    
    print(f"\nTesting {len(test_data)} instruments...")
    
    try:
        response = requests.post(
            f"{api_base}/api/calculate",
            json={"data": test_data, "instrument_type": "money_market", "params": {}}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nResponse structure:")
            print(f"  Status: {response.status_code}")
            print(f"  Has 'calculations': {'calculations' in result}")
            print(f"  Has 'data': {'data' in result}")
            
            # Use correct key
            calculations = result.get('calculations', result.get('data', []))
            print(f"  Calculations: {len(calculations)} items")
            
            if calculations:
                first = calculations[0]
                print(f"\n  Sample fields:")
                print(f"    principal: {first.get('principal', 'N/A')}")
                print(f"    interest_earned: {first.get('interest_earned', 'N/A')}")
                print(f"    annual_yield: {first.get('annual_yield', 'N/A')}")
        else:
            print(f"  Error: {response.status_code}")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()