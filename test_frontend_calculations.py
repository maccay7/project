import requests
import os
import json

def run_tests():
    print("Frontend Calculations Test")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    test_data_json = os.environ.get('TEST_DATA', '')
    
    if not test_data_json:
        print("\nNOTE: No TEST_DATA provided")
        print("Data comes from frontend upload, not from test script")
        print("\nChecking if backend is reachable...")
        
        try:
            response = requests.options(f"{api_base}/api/calculate")
            print(f"  Backend: {api_base}")
            print("  Status: Ready")
        except:
            print("  Error: Backend not reachable")
        
        print("\n" + "=" * 40)
        print("Test Complete")
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
            
            print("\n2. Results:")
            for calc in calcs[:4]:
                name = calc.get('instrument_type', calc.get('instrument_name', 'Unknown'))
                principal = calc.get('principal', 0)
                interest = calc.get('interest_earned', 0)
                
                print(f"\n  {name}:")
                print(f"    Principal: ${principal:,.2f}")
                print(f"    Interest:  ${interest:,.2f}")
        else:
            print(f"  Error: {response.status_code}")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()