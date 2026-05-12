import requests
import os

def run_tests():
    print("Testing Clean Endpoint")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    
    print("\n1. Checking if API is reachable...")
    try:
        resp = requests.options(f"{api_base}/api/clean")
        print(f"  OK - API reachable")
    except Exception as e:
        print(f"  Error: {e}")
        return
    
    print("\n2. Data comes from frontend upload")
    print("  - Upload a file in the frontend")
    print("  - Cleaning will process your data")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()