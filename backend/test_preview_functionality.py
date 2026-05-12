import requests
import os

def test_upload():
    print("Testing Upload Endpoint")
    print("=" * 40)
    
    api_url = os.environ.get('API_URL', 'http://localhost:5000/api/upload')
    
    print("\n1. Checking if API is reachable...")
    try:
        resp = requests.options(api_url)
        if resp.status_code < 500:
            print(f"  OK - Upload endpoint reachable")
        else:
            print(f"  Error: {resp.status_code}")
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