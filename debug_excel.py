import requests
import openpyxl
from io import BytesIO

# Create a simple Excel file with basic headers
workbook = openpyxl.Workbook()
sheet = workbook.active

# Add simple headers
sheet['A1'] = 'Name'
sheet['B1'] = 'Age'
sheet['C1'] = 'City'

# Add sample data
sheet['A2'] = 'John'
sheet['B2'] = 25
sheet['C2'] = 'New York'

sheet['A3'] = 'Jane'
sheet['B3'] = 30
sheet['C3'] = 'London'

# Save to BytesIO
excel_buffer = BytesIO()
workbook.save(excel_buffer)
excel_buffer.seek(0)

# Test upload
url = "http://localhost:5000/api/upload"
files = {
    'file': ('simple_test.xlsx', excel_buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
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
