import requests
import os

def run_tests():
    print("Testing Backend Connectivity")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    
    endpoints = [
        '/api/calculate',
        '/api/fred-yield-curve',
        '/api/upload',
        '/api/clean',
        '/api/datasets'
    ]
    
    print(f"\nBackend: {api_base}")
    print("\nChecking endpoints...")
    
    for endpoint in endpoints:
        url = f"{api_base}{endpoint}"
        try:
            if endpoint == '/api/calculate':
                resp = requests.options(url)
            else:
                resp = requests.get(url)
            
            if resp.status_code < 500:
                print(f"  OK - {endpoint}")
            else:
                print(f"  FAIL - {endpoint} ({resp.status_code})")
        except:
            print(f"  ERROR - {endpoint} (unreachable)")
    
    print("\n" + "=" * 40)
    print("Test Complete")
    print("\nNote: Upload data through frontend to test full functionality")

if __name__ == "__main__":
    run_tests()