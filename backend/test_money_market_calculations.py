import requests
import os
import json

def run_tests():
    print("Testing Money Market Calculations")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    test_data = os.environ.get('TEST_DATA', '')
    
    if not test_data:
        print("\nNOTE: Data comes from frontend upload")
        try:
            resp = requests.options(f"{api_base}/api/calculate")
            print(f"  Backend: {api_base}")
            print("  Status: Ready")
        except:
            print("  Error: Backend not reachable")
        return
    
    try:
        data = json.loads(test_data)
        print(f"\nTesting {len(data)} instruments...")
        
        resp = requests.post(f"{api_base}/api/calculate", 
            json={"data": data, "instrument_type": "money_market", "params": {}})
        
        if resp.status_code == 200:
            calcs = resp.json().get('calculations', [])
            print(f"\nResults: {len(calcs)} calculations")
            
            for calc in calcs[:3]:
                print(f"\n{calc.get('instrument_type', 'Unknown')}:")
                print(f"  Principal: ${calc.get('principal', 0):,.2f}")
                print(f"  Interest:  ${calc.get('interest_earned', 0):,.2f}")
                print(f"  Yield:     {calc.get('annual_yield', 0):.2f}%")
        else:
            print(f"Error: {resp.status_code}")
    except:
        print("Error: Invalid TEST_DATA format")

if __name__ == "__main__":
    run_tests()