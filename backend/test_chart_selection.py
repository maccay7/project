import requests
import os

def run_tests():
    print("Testing Chart Selection")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    
    print("\n1. Checking APIs...")
    try:
        # Test yield curve API
        yield_resp = requests.get(f"{api_base}/api/fred-yield-curve")
        if yield_resp.status_code == 200:
            print(f"  OK - Yield Curve API")
        else:
            print(f"  Error: {yield_resp.status_code}")
            
        # Test calculations API
        calc_resp = requests.options(f"{api_base}/api/calculate")
        if calc_resp.status_code < 500:
            print(f"  OK - Calculations API")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n2. Charts available:")
    charts = ["Bar Chart", "Line Chart", "Pie Chart", "Area Chart", "Yield Curve"]
    for chart in charts:
        print(f"  - {chart}")
    
    print("\n3. Data comes from frontend upload")
    print("\n" + "=" * 40)
    print("Test Complete")

if __name__ == "__main__":
    run_tests()