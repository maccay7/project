import requests
import openpyxl
from io import BytesIO

# Create a test Excel file with more than 10 rows to test pagination
workbook = openpyxl.Workbook()
sheet = workbook.active

# Add headers
sheet['A1'] = 'faceValue'
sheet['B1'] = 'purchasePrice' 
sheet['C1'] = 'daysToMaturity'

# Add 25 rows of data to test pagination
for i in range(1, 26):
    sheet[f'A{i+1}'] = 1000 + i
    sheet[f'B{i+1}'] = 950 + i
    sheet[f'C{i+1}'] = 90 * i

# Save to BytesIO
excel_buffer = BytesIO()
workbook.save(excel_buffer)
excel_buffer.seek(0)

# Test upload
url = "http://localhost:5000/api/upload"
files = {
    'file': ('test_pagination.xlsx', excel_buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
}
data = {
    'instrument_type': 'treasury_bills'
}

try:
    response = requests.post(url, files=files, data=data)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"Data rows: {len(result.get('data', {}).get('data', []))}")
        print(f"File name: {result.get('data', {}).get('name')}")
        
        # Show first few rows
        data_rows = result.get('data', {}).get('data', [])
        if data_rows:
            print("\nFirst 3 rows of data:")
            for i, row in enumerate(data_rows[:3]):
                print(f"Row {i+1}: {row}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
