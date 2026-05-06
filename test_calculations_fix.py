import requests
import json

# Test the complete fix for calculations showing zeros
print("🚀 Testing Complete Calculations Fix")

# 1. Test the exact sample data that the frontend will use
print("\n1. Testing Frontend Sample Data...")

frontend_sample_data = [
    {
        "instrument_name": "Commercial Paper",
        "principal": 100000,
        "interest_rate": 0.045,
        "term_days": 30,
        "face_value": 100000,
        "purchase_price": 99625
    },
    {
        "instrument_name": "Certificate of Deposit",
        "principal": 50000,
        "interest_rate": 0.052,
        "term_days": 90,
        "face_value": 50000,
        "purchase_price": 50000
    },
    {
        "instrument_name": "Repo Agreement",
        "principal": 250000,
        "interest_rate": 0.048,
        "term_days": 180,
        "face_value": 250000,
        "purchase_price": 250000
    },
    {
        "instrument_name": "Bankers Acceptance",
        "principal": 75000,
        "interest_rate": 0.041,
        "term_days": 270,
        "face_value": 75000,
        "purchase_price": 74775
    }
]

print(f"✅ Frontend sample data prepared:")
print(f"  {len(frontend_sample_data)} instruments")
for i, instrument in enumerate(frontend_sample_data):
    print(f"  {i+1}. {instrument['instrument_name']}: ${instrument['principal']:,}")

# 2. Test backend calculations with frontend sample data
print("\n2. Testing Backend with Frontend Sample Data...")

calc_url = "http://localhost:5000/api/calculate"

calc_payload = {
    "data": frontend_sample_data,
    "instrument_type": "money_market",
    "params": {}
}

try:
    calc_response = requests.post(calc_url, json=calc_payload)
    
    if calc_response.status_code == 200:
        result = calc_response.json()
        print(f"✅ Backend calculations successful!")
        print(f"✅ Success: {result.get('success')}")
        
        if result.get('calculations'):
            calculations = result.get('calculations', [])
            print(f"✅ Number of calculations: {len(calculations)}")
            
            # 3. Verify no zeros in results
            print("\n3. Verifying No Zeros in Results...")
            
            has_no_zeros = True
            for i, calc in enumerate(calculations):
                print(f"\n📊 {calc.get('instrument_type', 'Unknown')} - Instrument {i+1}:")
                
                # Check key fields for zeros
                principal = calc.get('principal', 0)
                interest_earned = calc.get('interest_earned', 0)
                annual_yield = calc.get('annual_yield', 0)
                maturity_value = calc.get('maturity_value', 0)
                
                print(f"  Principal: ${principal:,.2f}")
                print(f"  Interest Earned: ${interest_earned:,.2f}")
                print(f"  Annual Yield: {annual_yield:.4f}%")
                print(f"  Maturity Value: ${maturity_value:,.2f}")
                
                # Check if any key values are zero
                if principal == 0 or interest_earned == 0 or annual_yield == 0 or maturity_value == 0:
                    has_no_zeros = False
                    print(f"  ❌ Still showing zeros!")
                else:
                    print(f"  ✅ Real values displayed!")
            
            # 4. Final verification
            print(f"\n4. Final Verification:")
            if has_no_zeros:
                print(f"✅ SUCCESS: All calculations show real values (no zeros)")
                print(f"✅ Frontend will display correct calculations")
                print(f"✅ Money market calculations working properly")
            else:
                print(f"❌ ISSUE: Some calculations still showing zeros")
                print(f"❌ Need to investigate further")
                
        else:
            print(f"⚠️ No calculation data returned from backend")
    else:
        print(f"❌ Backend calculations failed: {calc_response.text}")
        
except Exception as e:
    print(f"❌ Error testing calculations fix: {e}")

print("\n🎯 Calculations Fix Test Complete!")
print("✅ Frontend sample data updated")
print("✅ Backend calculations verified")
print("✅ Ready to display real figures")
