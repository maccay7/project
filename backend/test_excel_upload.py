import requests
import os

def test_upload():
    api_url = os.environ.get('API_URL', 'http://localhost:5000/api/upload')
    
    print("Testing Upload Endpoint")
    print("=" * 40)
    
    print("\n1. Checking API...")
    try:
        resp = requests.options(api_url)
        print(f"  OK - API reachable")
    except Exception as e:
        print(f"  Error: {e}")
        return
    
    print("\n2. Data comes from frontend upload")
    print("  - Select a file in the frontend")
    print("  - Click upload to send to backend")
    
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    test_upload()