import requests
import os

def test_upload():
    print("Testing Upload Endpoint")
    print("=" * 30)
    
    api_url = os.environ.get('API_URL', 'http://localhost:5000/api/upload')
    
    print(f"\nAPI: {api_url}")
    print("\n1. Checking endpoint...")
    
    try:
        resp = requests.options(api_url)
        print("  OK - Endpoint reachable" if resp.status_code < 500 else f"  Error: {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
        return
    
    print("\n2. Data comes from frontend upload")
    print("  - Select Excel file in frontend")
    print("  - Click upload button")
    
    print("\n" + "=" * 30)
    print("Test Complete")

if __name__ == "__main__":
    test_upload()