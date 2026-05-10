import requests
import json
import os
import sys

def load_config():
    """Load all configuration from environment variables"""
    return {
        'api_base': os.environ.get('API_BASE_URL', 'http://localhost:5000'),
        'instrument_type': os.environ.get('INSTRUMENT_TYPE', 'money_market'),
        'test_data': os.environ.get('TEST_DATA', ''),
        'verbose': os.environ.get('VERBOSE', 'true').lower() == 'true'
    }

def load_test_data(config):
    """Load test data from environment variable"""
    test_data_json = config['test_data']
    
    if not test_data_json:
        print("Error: No test data found. Set TEST_DATA environment variable")
        print('Example: export TEST_DATA=\'[{"name":"test","value":100}]\'')
        sys.exit(1)
    
    try:
        return json.loads(test_data_json)
    except json.JSONDecodeError as e:
        print(f"Error: TEST_DATA is not valid JSON: {e}")
        sys.exit(1)

def run_tests(config, test_data):
    """Run the API tests"""
    calc_url = f"{config['api_base']}/api/calculate"
    yield_url = f"{config['api_base']}/api/fred-yield-curve"
    
    print("Testing Visualizations")
    print("=" * 40)
    print(f"API Base: {config['api_base']}")
    print(f"Records: {len(test_data)}")
    print(f"Instrument: {config['instrument_type']}")
    
    payload = {
        "data": test_data,
        "instrument_type": config['instrument_type'],
        "params": {}
    }
    
    # Test calculations API
    print("\n1. Testing Calculations API...")
    try:
        response = requests.post(calc_url, json=payload)
        
        if response.status_code != 200:
            print(f"  Error: API returned {response.status_code}")
            return False
        
        result = response.json()
        calculations = result.get('calculations', [])
        print(f"  OK - Calculations: {len(calculations)}")
        
        # Show sample results
        if calculations and config['verbose']:
            print("\n  Sample Results:")
            calc = calculations[0]
            print(f"    Principal: ${calc.get('principal', 0):,.2f}")
            print(f"    Interest:  ${calc.get('interest_earned', 0):,.2f}")
            print(f"    Yield:     {calc.get('annual_yield', 0):.2f}%")
        
    except Exception as e:
        print(f"  Error: {e}")
        return False
    
    # Test yield curve API
    print("\n2. Testing Yield Curve API...")
    try:
        response = requests.get(yield_url)
        
        if response.status_code != 200:
            print(f"  Error: API returned {response.status_code}")
            return False
        
        data = response.json()
        curve_data = data.get('data', {})
        rates = curve_data.get('current', [])
        print(f"  OK - Yield Curve: {len(rates)} rates available")
        
        if config['verbose'] and rates:
            print(f"    Latest rates: {rates[:3]}")
        
    except Exception as e:
        print(f"  Error: {e}")
        return False
    
    print("\nResult: Success")
    return True

def main():
    config = load_config()
    test_data = load_test_data(config)
    success = run_tests(config, test_data)
    
    print("\n" + "=" * 40)
    print("Test Complete" if success else "Test Failed")
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()