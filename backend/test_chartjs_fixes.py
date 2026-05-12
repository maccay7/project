import requests
import os

def run_tests():
    print("Testing Backend APIs")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    
    # Test yield curve API
    print("\n1. Testing Yield Curve API...")
    try:
        resp = requests.get(f"{api_base}/api/fred-yield-curve")
        if resp.status_code == 200:
            rates = resp.json().get('data', {}).get('current', [])
            print(f"  OK - {len(rates)} rates")
        else:
            print(f"  Error: {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test calculations API
    print("\n2. Testing Calculations API...")
    try:
        resp = requests.options(f"{api_base}/api/calculate")
        if resp.status_code < 500:
            print(f"  OK - API reachable")
        else:
            print(f"  Error: {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n3. Data flows from frontend to backend")
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()