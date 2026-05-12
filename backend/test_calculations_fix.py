import requests
import os
import json

def run_tests():
    print("Testing Calculations Fix")
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
            
            # Verify no zeros
            print("\n  Results:")
            all_valid = True
            for calc in calcs:
                name = calc.get('instrument_type', 'Unknown')
                principal = calc.get('principal', 0)
                interest = calc.get('interest_earned', 0)
                
                if principal > 0 and interest > 0:
                    print(f"    {name}: ${principal:,.2f} principal, ${interest:,.2f} interest")
                else:
                    print(f"    {name}: WARNING - zero values")
                    all_valid = False
            
            if all_valid:
                print("\n  Result: Success - No zeros")
            else:
                print("\n  Result: Warning - Some zeros found")
        else:
            print(f"  Error: {response.status_code}")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()