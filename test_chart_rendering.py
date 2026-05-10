import requests
import os
import json

def run_tests():
    print("Testing Backend API")
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
            calcs = response.json().get('calculations', [])
            print(f"  OK - {len(calcs)} calculations")
            
            # Verify data exists for charts (backend concern)
            if calcs:
                has_face_values = all(c.get('face_value', 0) > 0 for c in calcs)
                has_prices = all(c.get('purchase_price', 0) > 0 for c in calcs)
                has_yields = all(c.get('annual_yield', 0) > 0 for c in calcs)
                has_principals = all(c.get('principal', 0) > 0 for c in calcs)
                
                print("\n  Data validation:")
                print(f"    Face values: {'OK' if has_face_values else 'Missing'}")
                print(f"    Prices: {'OK' if has_prices else 'Missing'}")
                print(f"    Yields: {'OK' if has_yields else 'Missing'}")
                print(f"    Principals: {'OK' if has_principals else 'Missing'}")
            
            print("\n  Result: Success")
        else:
            print(f"  Error: {response.status_code}")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()