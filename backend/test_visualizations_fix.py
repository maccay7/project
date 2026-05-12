import requests
import os
import sys

def run_tests():
    print("Testing Visualizations")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    
    # Test yield curve API
    print("\n1. Testing Yield Curve API...")
    try:
        resp = requests.get(f"{api_base}/api/fred-yield-curve")
        if resp.status_code == 200:
            rates = resp.json().get('data', {}).get('current', [])
            print(f"  OK - {len(rates)} rates available")
        else:
            print(f"  Error: {resp.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"  Error: {e}")
        sys.exit(1)
    
    # Test calculations API
    print("\n2. Testing Calculations API...")
    try:
        resp = requests.options(f"{api_base}/api/calculate")
        if resp.status_code < 500:
            print(f"  OK - API reachable")
        else:
            print(f"  Error: {resp.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"  Error: {e}")
        sys.exit(1)
    
    print("\n3. Data comes from frontend upload")
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()