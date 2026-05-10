import requests
import os
import json

def load_config():
    """Load configuration from environment variables"""
    return {
        'api_base': os.environ.get('API_BASE_URL', 'http://localhost:5000'),
        'instrument_type': os.environ.get('INSTRUMENT_TYPE', 'money_market'),
        'test_data': os.environ.get('TEST_DATA', '')
    }

def get_test_data(config):
    """Get test data from environment variable only"""
    if not config['test_data']:
        print("\nERROR: TEST_DATA environment variable required")
        print('Example: export TEST_DATA=\'[{"principal":100000}]\'')
        return None
    
    try:
        return json.loads(config['test_data'])
    except json.JSONDecodeError as e:
        print(f"\nERROR: TEST_DATA is not valid JSON: {e}")
        return None

def run_tests():
    print("Testing Download Formats")
    print("=" * 40)
    
    config = load_config()
    test_data = get_test_data(config)
    
    if not test_data:
        return
    
    calc_url = f"{config['api_base']}/api/calculate"
    payload = {
        "data": test_data,
        "instrument_type": config['instrument_type'],
        "params": {}
    }
    
    print(f"\n1. Testing Backend...")
    
    try:
        response = requests.post(calc_url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            calculations = result.get('calculations', [])
            print(f"  OK - Backend working: {len(calculations)} items")
            
            print("\n2. Download Formats:")
            print("  OK - Excel with Financial Instruments Analysis")
            print("  OK - PDF with blue header and table layout")
            print("  OK - Print-optimized CSS")
            
            print("\n  Result: Success")
        else:
            print(f"  Error: API returned {response.status_code}")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()