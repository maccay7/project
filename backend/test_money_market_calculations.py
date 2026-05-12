import requests
import os
import json

def run_tests():
    print("Testing Money Market Calculations")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    
    # Get test data from environment (comes from frontend upload)
    test_data_json = os.environ.get('TEST_DATA', '')
    
    if not test_data_json:
        print("\nNOTE: No TEST_DATA provided")
        print("Data comes from frontend upload, not from test script")
        print("\nChecking if backend is reachable...")
        
        try:
            response = requests.options(f"{api_base}/api/calculate")
            print(f"  Backend: {api_base}")
            print("  Status: Ready to receive data from frontend")
        except:
            print("  Error: Backend not reachable")
        
        print("\n" + "=" * 40)
        print("Test Complete")
        return
    
    try:
        test_data = json.loads(test_data_json)
    except:
        print("ERROR: TEST_DATA is not valid JSON")
        return
    
    print(f"\nTesting {len(test_data)} instruments...")
    
    try:
        response = requests.post(
            f"{api_base}/api/calculate",
            json={"data": test_data, "instrument_type": "money_market", "params": {}}
        )
        
        if response.status_code == 200:
            calcs = response.json().get('calculations', [])
            print(f"\nResults: {len(calcs)} calculations")
            
            for calc in calcs[:3]:  # Show first 3 only
                name = calc.get('instrument_type', 'Unknown')
                print(f"\n{name}:")
                print(f"  Principal: ${calc.get('principal', 0):,.2f}")
                print(f"  Interest:  ${calc.get('interest_earned', 0):,.2f}")
                print(f"  Yield:     {calc.get('annual_yield', 0):.2f}%")
        else:
            print(f"Error: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_tests()