import requests
import os

def test_upload():
    print("Testing Upload Endpoint")
    print("=" * 30)
    
    api_url = os.environ.get('API_URL', 'http://localhost:5000/api/upload')
    
    print(f"\nAPI: {api_url}")
    print("\n1. Checking if endpoint is reachable...")
    
    try:
        resp = requests.options(api_url)
        if resp.status_code < 500:
            print("  OK - Upload endpoint reachable")
        else:
            print(f"  Error: {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
        return
    
    print("\n2. Data comes from frontend upload")
    print("  - Select a CSV file in frontend")
    print("  - Data will be sent to this endpoint")
    
    print("\n" + "=" * 30)
    print("Test Complete")

if __name__ == "__main__":
    test_upload()