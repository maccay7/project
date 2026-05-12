import requests
import os

def run_tests():
    print("Frontend Calculations Test")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    
    print("\n1. Checking backend...")
    try:
        resp = requests.options(f"{api_base}/api/calculate")
        print(f"  OK - Backend reachable")
    except Exception as e:
        print(f"  Error: {e}")
        return
    
    print("\n2. Data source: Frontend upload")
    print("  - Upload file in frontend")
    print("  - Calculations will appear here")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()