import requests
import os
import json

def load_config():
    """Load all configuration from environment variables"""
    return {
        'api_base': os.environ.get('API_BASE_URL', 'http://localhost:5000'),
        'instrument_type': os.environ.get('INSTRUMENT_TYPE', 'money_market'),
        'test_data': os.environ.get('TEST_DATA', '')
    }

def run_tests():
    print("Testing Yield Curve Integration")
    print("=" * 40)
    
    config = load_config()
    
    # Get test data from environment
    test_data = []
    if config['test_data']:
        try:
            test_data = json.loads(config['test_data'])
        except:
            pass
    
    print(f"\nAPI: {config['api_base']}")
    print(f"Instrument: {config['instrument_type']}")
    print(f"Records: {len(test_data)}")
    
    # Set up URLs
    calc_url = f"{config['api_base']}/api/calculate"
    yield_url = f"{config['api_base']}/api/fred-yield-curve"
    
    # Test calculations API (POST with data)
    print("\n1. Testing Calculations API...")
    try:
        calc_resp = requests.post(
            calc_url,
            json={"data": test_data, "instrument_type": config['instrument_type'], "params": {}}
        )
        
        if calc_resp.status_code == 200:
            result = calc_resp.json()
            calcs = result.get('calculations', [])
            print(f"  OK - Calculations: {len(calcs)} items")
            if calcs:
                print(f"      Sample: ${calcs[0].get('principal', 0):,.2f} principal")
        else:
            print(f"  FAIL - Status: {calc_resp.status_code}")
            
    except Exception as e:
        print(f"  ERROR - {e}")
    
    # Test yield curve API (GET)
    print("\n2. Testing Yield Curve API...")
    try:
        yield_resp = requests.get(yield_url)
        
        if yield_resp.status_code == 200:
            data = yield_resp.json()
            curve_data = data.get('data', {})
            rates = curve_data.get('current', [])
            labels = curve_data.get('labels', [])
            print(f"  OK - Yield curve available")
            print(f"      Labels: {labels}")
            print(f"      Rates: {rates}")
        else:
            print(f"  FAIL - Status: {yield_resp.status_code}")
            
    except Exception as e:
        print(f"  ERROR - {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()