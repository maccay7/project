import requests
import os

def run_tests():
    print("Testing Backend API")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    
    print("\n1. Checking API...")
    try:
        resp = requests.options(f"{api_base}/api/calculate")
        print(f"  OK - API reachable")
    except Exception as e:
        print(f"  Error: {e}")
        return
    
    print("\n2. Data comes from frontend upload")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()