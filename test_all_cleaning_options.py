import requests
import json

# Test the cleaning endpoint with sample data that has various issues
url = "http://localhost:5000/api/clean"

# Sample data with various cleaning issues
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
        "Fund_Name": "  fund_one  ",
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
        "Maturity_Date": "01/01/2024",
        "Issue_Date": "01/01/2023",
        "Valuation_date": "2024-04-28",
        "Tenure": "1 years"
    },
    {
        "Days_to_Maturity": "Day 2",  # Duplicate row
        "Years_to_Maturity": "1 years",
        "Rate": "4.5%",
        "Nominal": "$1,000",
        "Carrying_Value": "$950",
        "Maturity_Value": "$1,000",
        "Discount_Rate": "0.05",
        "Present_Value": "$900",
        "Impairment_US": "$10",
        "Impairment_ZWL": "$100",
        "Fund_Name": "  fund_one  ",
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
        "Maturity_Date": "01/01/2024",
        "Issue_Date": "01/01/2023",
        "Valuation_date": "2024-04-28",
        "Tenure": "1 years"
    },
    {
        "Days_to_Maturity": "",  # Missing value
        "Years_to_Maturity": "2 years", 
        "Rate": "",  # Missing value
        "Nominal": "$1,100",
        "Carrying_Value": "",  # Missing value
        "Maturity_Value": "$1,100",
        "Discount_Rate": "0.06",
        "Present_Value": "$920",
        "Impairment_US": None,  # Null value
        "Impairment_ZWL": "$150",
        "Fund_Name": "  fund_two  ",
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
        "Maturity_Date": "02/01/2024",
        "Issue_Date": "02/01/2023",
        "Valuation_date": "2024-04-28",
        "Tenure": "2 years"
    },
    {
        "Days_to_Maturity": "Day 4",
        "Years_to_Maturity": "3 years",
        "Rate": "4.7%",
        "Nominal": "$1,200",
        "Carrying_Value": "$970",
        "Maturity_Value": "$1,200",
        "Discount_Rate": "0.07",
        "Present_Value": "$940",
        "Impairment_US": "$20",
        "Impairment_ZWL": "$200",
        "Fund_Name": "  fund_three  ",
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
        "Maturity_Date": "03/01/2024",
        "Issue_Date": "03/01/2023",
        "Valuation_date": "2024-04-28",
        "Tenure": "3 years"
    }
]

# Test all cleaning options
cleaning_options = {
    "removeDuplicates": True,
    "fillMissingValues": True,
    "removeOutliers": False,
    "removeEmptyRows": True,
    "standardizeText": True,
    "trimWhitespace": True,
    "normalizeNumbers": True,
    "formatDates": True,
    "validateEmails": False,
    "convertDataTypes": False,
    "standardizeCurrency": True,
    "normalizePercentages": True,
    "validateRanges": False,
    "checkConsistency": False,
    "validatePatterns": False,
    "removeSpecialChars": False,
    "standardizePhoneNumbers": False,
    "normalizeAddresses": False,
    "cleanPostalCodes": False
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
        
        # Show all cleaning stats
        stats = result.get('stats', {})
        print(f"\nCleaning Results:")
        print(f"  Duplicates removed: {stats.get('duplicates_removed', 0)}")
        print(f"  Missing values filled: {stats.get('missing_values_filled', 0)}")
        print(f"  Empty rows removed: {stats.get('empty_rows_removed', 0)}")
        print(f"  Text standardized: {stats.get('text_standardized', 0)}")
        print(f"  Whitespace trimmed: {stats.get('whitespace_trimmed', 0)}")
        print(f"  Numbers normalized: {stats.get('numbers_normalized', 0)}")
        print(f"  Dates formatted: {stats.get('dates_formatted', 0)}")
        print(f"  Currency standardized: {stats.get('currency_standardized', 0)}")
        print(f"  Percentages normalized: {stats.get('percentages_normalized', 0)}")
        print(f"  Total operations applied: {stats.get('total_operations_applied', 0)}")
        
        # Show cleaned data preview
        cleaned_data = result.get('data', [])
        if cleaned_data:
            print(f"\nCleaned Data Preview (first 2 rows):")
            for i, row in enumerate(cleaned_data[:2]):
                print(f"Row {i+1}:")
                for key, value in list(row.items())[:8]:  # Show first 8 columns
                    print(f"  {key}: {value}")
                print()
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
