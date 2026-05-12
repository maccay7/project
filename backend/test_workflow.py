import requests
import os

def main():
    print("Testing Complete Workflow")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    
    print(f"\nAPI Base: {api_base}")
    
    # Test upload endpoint
    print("\n1. Testing Upload Endpoint...")
    try:
        resp = requests.options(f"{api_base}/api/upload")
        print(f"  OK - Upload endpoint reachable" if resp.status_code < 500 else f"  Error: {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test clean endpoint
    print("\n2. Testing Clean Endpoint...")
    try:
        resp = requests.options(f"{api_base}/api/clean")
        print(f"  OK - Clean endpoint reachable" if resp.status_code < 500 else f"  Error: {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test delete endpoint
    print("\n3. Testing Delete Endpoint...")
    try:
        resp = requests.options(f"{api_base}/api/delete-dataset")
        print(f"  OK - Delete endpoint reachable" if resp.status_code < 500 else f"  Error: {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\nNote: Upload data through frontend to test full functionality")
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    main()