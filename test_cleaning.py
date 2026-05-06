import requests
import json

# Test the cleaning endpoint with sample data
url = "http://localhost:5000/api/clean"

# Sample data similar to what would come from an uploaded Excel file
test_data = [
    {
        "Days_to_Maturity": "Day 1",
        "Years_to_Maturity": "1 years",
        "Rate": "4.5%",
        "Nominal": "$1,000",
        "Carrying_Value": "$950",
        "Maturity_Value": "$1,000",
        "Discount_Rate": "0.05",
        "Present_Value": "$900",
        "Impairment_US": "$10",
        "Impairment_ZWL": "$100",
        "Fund_Name": "Fund_1",
        "NSS_rates": "3.5%",
        "Discount_rates": "0.04",
        "Time_value": "$50",
        "Present_Value": "$850",
        "Time_value_impairment": "$5",
        "Credit_Impairment": "$2",
        "total_Impairment_US": "$15",
        "total_Impairment_ZWL": "$150",
        "Portfolio": "Portfolio_1",
        "Short_Name": "Short_1",
        "Counterparty": "Counterparty_1",
        "Maturity_Date": "2024-01-01",
        "Issue_Date": "2023-01-01",
        "Valuation_date": "2024-04-28",
        "Tenure": "1 years"
    },
    {
        "Days_to_Maturity": "Day 2",
        "Years_to_Maturity": "2 years", 
        "Rate": "4.6%",
        "Nominal": "$1,100",
        "Carrying_Value": "$960",
        "Maturity_Value": "$1,100",
        "Discount_Rate": "0.06",
        "Present_Value": "$920",
        "Impairment_US": "$15",
        "Impairment_ZWL": "$150",
        "Fund_Name": "Fund_2",
        "NSS_rates": "3.55%",
        "Discount_rates": "0.05",
        "Time_value": "$60",
        "Present_Value": "$870",
        "Time_value_impairment": "$7",
        "Credit_Impairment": "$3",
        "total_Impairment_US": "$25",
        "total_Impairment_ZWL": "$250",
        "Portfolio": "Portfolio_2",
        "Short_Name": "Short_2",
        "Counterparty": "Counterparty_2",
        "Maturity_Date": "2024-02-01",
        "Issue_Date": "2023-02-01",
        "Valuation_date": "2024-04-28",
        "Tenure": "2 years"
    },
    {
        "Days_to_Maturity": "Day 1",  # Duplicate row
        "Years_to_Maturity": "1 years",
        "Rate": "4.5%",
        "Nominal": "$1,000",
        "Carrying_Value": "$950",
        "Maturity_Value": "$1,000",
        "Discount_Rate": "0.05",
        "Present_Value": "$900",
        "Impairment_US": "$10",
        "Impairment_ZWL": "$100",
        "Fund_Name": "Fund_1",
        "NSS_rates": "3.5%",
        "Discount_rates": "0.04",
        "Time_value": "$50",
        "Present_Value": "$850",
        "Time_value_impairment": "$5",
        "Credit_Impairment": "$2",
        "total_Impairment_US": "$15",
        "total_Impairment_ZWL": "$150",
        "Portfolio": "Portfolio_1",
        "Short_Name": "Short_1",
        "Counterparty": "Counterparty_1",
        "Maturity_Date": "2024-01-01",
        "Issue_Date": "2023-01-01",
        "Valuation_date": "2024-04-28",
        "Tenure": "1 years"
    },
    {
        "Days_to_Maturity": "",  # Missing value
        "Years_to_Maturity": "3 years",
        "Rate": "",  # Missing value
        "Nominal": "$1,200",
        "Carrying_Value": "",  # Missing value
        "Maturity_Value": "$1,200",
        "Discount_Rate": "0.07",
        "Present_Value": "$940",
        "Impairment_US": None,  # Null value
        "Impairment_ZWL": "$200",
        "Fund_Name": "Fund_3",
        "NSS_rates": "3.6%",
        "Discount_rates": "0.06",
        "Time_value": "$70",
        "Present_Value": "$890",
        "Time_value_impairment": "$9",
        "Credit_Impairment": "$4",
        "total_Impairment_US": "$35",
        "total_Impairment_ZWL": "$350",
        "Portfolio": "Portfolio_3",
        "Short_Name": "Short_3",
        "Counterparty": "Counterparty_3",
        "Maturity_Date": "2024-03-01",
        "Issue_Date": "2023-03-01",
        "Valuation_date": "2024-04-28",
        "Tenure": "3 years"
    }
]

# Test cleaning options
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
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"Original rows: {result.get('stats', {}).get('original_rows')}")
        print(f"Cleaned rows: {result.get('stats', {}).get('cleaned_rows')}")
        print(f"Duplicates removed: {result.get('stats', {}).get('duplicates_removed')}")
        print(f"Missing values filled: {result.get('stats', {}).get('missing_values_filled')}")
        print(f"Outliers removed: {result.get('stats', {}).get('outliers_removed')}")
        
        # Show first few cleaned rows
        cleaned_data = result.get('data', [])
        if cleaned_data:
            print(f"\nFirst 3 cleaned rows:")
            for i, row in enumerate(cleaned_data[:3]):
                print(f"Row {i+1}: {dict(list(row.items())[:5])}...")  # Show first 5 columns
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
