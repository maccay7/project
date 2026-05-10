import requests
import os
import json

def run_tests():
    print("Testing Backend APIs")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    test_data_json = os.environ.get('TEST_DATA', '')
    
    # Test yield curve API (no data needed)
    print("\n1. Testing FRED Yield Curve API...")
    try:
        response = requests.get(f"{api_base}/api/fred-yield-curve")
        
        if response.status_code == 200:
            data = response.json()
            curve_data = data.get('data', {})
            rates = curve_data.get('current', [])
            print(f"  OK - Yield curve: {len(rates)} rates")
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
    
    print(f"  Testing {len(test_data)} instruments...")
    
    try:
        response = requests.post(
            f"{api_base}/api/calculate",
            json={"data": test_data, "instrument_type": "money_market", "params": {}}
        )
        
        if response.status_code == 200:
            calcs = response.json().get('calculations', [])
            print(f"  OK - Calculations: {len(calcs)} items")
            
            # Show one sample result
            if calcs:
                c = calcs[0]
                print(f"\n  Sample result:")
                print(f"    Principal: ${c.get('principal', 0):,.2f}")
                print(f"    Interest:  ${c.get('interest_earned', 0):,.2f}")
                print(f"    Yield:     {c.get('annual_yield', 0):.2f}%")
        else:
            print(f"  Error: {response.status_code}")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()