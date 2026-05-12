import requests
import os
import json

def run_tests():
    print("Testing Clean Endpoint")
    print("=" * 40)
    
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    test_data_json = os.environ.get('TEST_DATA', '')
    
    if not test_data_json:
        print("\nERROR: TEST_DATA environment variable not set")
        return
    
    try:
        test_data = json.loads(test_data_json)
    except json.JSONDecodeError:
        print("\nERROR: TEST_DATA is not valid JSON")
        return
    
    clean_url = f"{api_base}/api/clean"
    
    cleaning_options = {
        "remove_duplicates": True,
        "fill_missing_values": True,
        "remove_outliers": True
    }
    
    payload = {
        "data": test_data,
        "options": cleaning_options
    }
    
    try:
        response = requests.post(clean_url, json=payload)
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            stats = result.get('stats', {})
            print(f"Original rows: {stats.get('original_rows')}")
            print(f"Cleaned rows: {stats.get('cleaned_rows')}")
            print(f"Duplicates removed: {stats.get('duplicates_removed')}")
            print(f"Missing values filled: {stats.get('missing_values_filled')}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_tests()