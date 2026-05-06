import requests

# Test the upload endpoint with a simple CSV
url = "http://localhost:5000/api/upload"

# Create a simple CSV file content
csv_content = """faceValue,purchasePrice,daysToMaturity
1000,950,90
1000,960,180
1000,970,270"""

# Create multipart form data
files = {
    'file': ('test.csv', csv_content, 'text/csv')
}
data = {
    'instrument_type': 'treasury_bills'
}

try:
    response = requests.post(url, files=files, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
