import requests
import openpyxl
from io import BytesIO

# Create a test Excel file with realistic column names
workbook = openpyxl.Workbook()
sheet = workbook.active

# Add realistic headers like those in financial datasets
sheet['A1'] = 'Face Value Amount'
sheet['B1'] = 'Purchase Price ($)'
sheet['C1'] = 'Days to Maturity'
sheet['D1'] = 'Yield Rate (%)'
sheet['E1'] = 'Discount Rate'

# Add sample data
for i in range(1, 15):
    sheet[f'A{i+1}'] = 1000 + (i * 100)
    sheet[f'B{i+1}'] = 950 + (i * 5)
    sheet[f'C{i+1}'] = 30 * i
    sheet[f'D{i+1}'] = 4.5 + (i * 0.1)
    sheet[f'E{i+1}'] = 0.05 + (i * 0.01)

# Save to BytesIO
excel_buffer = BytesIO()
workbook.save(excel_buffer)
excel_buffer.seek(0)

# Test upload
url = "http://localhost:5000/api/upload"
files = {
    'file': ('financial_data.xlsx', excel_buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
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
        
        # Show column headers from first row
        data_rows = result.get('data', {}).get('data', [])
        if data_rows:
            print("\nColumn Headers:")
            first_row = data_rows[0]
            for key in first_row.keys():
                print(f"  - {key}")
            
            print("\nFirst 3 rows of data:")
            for i, row in enumerate(data_rows[:3]):
                print(f"Row {i+1}: {row}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
