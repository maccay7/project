import requests
import os

def load_config():
    """Load configuration from environment variables"""
    return {
        'api_url': os.environ.get('API_URL', 'http://localhost:5000/api/upload'),
        'instrument_type': os.environ.get('INSTRUMENT_TYPE', 'treasury_bills'),
        'csv_data': os.environ.get('CSV_DATA', '')
    }

def get_csv_content(config):
    """Get CSV content from environment only"""
    if not config['csv_data']:
        print("\nERROR: CSV_DATA environment variable not set")
        return None
    
    return config['csv_data']

def test_upload():
    print("Testing Upload Endpoint")
    print("=" * 30)
    
    config = load_config()
    csv_content = get_csv_content(config)
    
    if not csv_content:
        return
    
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    data = {'instrument_type': config['instrument_type']}
    
    print(f"\nAPI: {config['api_url']}")
    
    try:
        response = requests.post(config['api_url'], files=files, data=data)
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success')}")
            
            if result.get('data'):
                file_data = result['data']
                print(f"Rows: {len(file_data.get('data', []))}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 30)
    print("Test Complete")

if __name__ == "__main__":
    test_upload()