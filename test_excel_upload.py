import requests
import openpyxl
from io import BytesIO

# Create a simple Excel file for testing
workbook = openpyxl.Workbook()
sheet = workbook.active

# Add headers
sheet['A1'] = 'faceValue'
sheet['B1'] = 'purchasePrice' 
sheet['C1'] = 'daysToMaturity'

# Add data
sheet['A2'] = 1000
sheet['B2'] = 950
sheet['C2'] = 90

sheet['A3'] = 1000
sheet['B3'] = 960
sheet['C3'] = 180

sheet['A4'] = 1000
sheet['B4'] = 970
sheet['C4'] = 270

# Save to BytesIO
excel_buffer = BytesIO()
workbook.save(excel_buffer)
excel_buffer.seek(0)

# Test upload
url = "http://localhost:5000/api/upload"
files = {
    'file': ('test_excel.xlsx', excel_buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
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
