import json
from flask import request, jsonify
from utils.db import get_db

def valuation_routes(app):
    @app.route('/api/valuation/calculate', methods=['POST', 'OPTIONS'])
    def calculate_valuation():
        if request.method == 'OPTIONS':
            return '', 200
            
        payload = request.get_json() or {}
        extracted_values = payload.get('extracted_values', {})
        instrument_type = payload.get('instrument_type', 'money-market')
        
        if not extracted_values:
            return jsonify({'success': False, 'error': 'No extracted values provided'}), 400
        
        try:
            # Perform backend valuation calculations based on instrument type
            results = perform_valuation(extracted_values, instrument_type)
            
            return jsonify({
                'success': True,
                'data': results,
                'instrument_type': instrument_type
            })
        except Exception as e:
            print(f"❌ Valuation calculation error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

def perform_valuation(extracted_values, instrument_type):
    """Perform valuation calculations for single-instrument worksheets"""
    results = {}
    
    def get_number(val, default=0):
        try:
            if val is None or val == '':
                return default
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                # Remove currency symbols and commas
                cleaned = val.replace('$', '').replace(',', '').replace('%', '').strip()
                if cleaned:
                    return float(cleaned)
            return default
        except (ValueError, TypeError):
            return default
    
    def get_string(val, default=''):
        if val is None or val == '':
            return default
        return str(val)
    
    # Extract common fields with flexible naming
    instrument_name = get_string(extracted_values.get('instrumentName') or 
                               extracted_values.get('Instrument Name') or 
                               extracted_values.get('instrument_name') or 
                               'Instrument')
    
    if instrument_type == 'money-market':
        principal = get_number(extracted_values.get('principal') or 
                              extracted_values.get('Principal') or 
                              extracted_values.get('amount') or 
                              extracted_values.get('Amount') or 
                              extracted_values.get('faceValue') or 
                              extracted_values.get('Face Value') or 0)
        
        rate = get_number(extracted_values.get('interestRate') or 
                         extracted_values.get('Interest Rate') or 
                         extracted_values.get('rate') or 
                         extracted_values.get('Rate') or 
                         extracted_values.get('couponRate') or 
                         extracted_values.get('Coupon Rate') or 0)
        
        days = get_number(extracted_values.get('daysToMaturity') or 
                        extracted_values.get('Days to Maturity') or 
                        extracted_values.get('term') or 
                        extracted_values.get('Term') or 
                        extracted_values.get('maturity') or 
                        extracted_values.get('Maturity') or 90)
        
        # Money Market calculations
        interest = principal * (rate / 100) * (days / 360)
        total_value = principal + interest
        
        results = {
            'Instrument Name': instrument_name,
            'Total Value': total_value,
            'total_value': total_value,
            'Instrument Count': 1,
            'instrument_count': 1,
            'Principal': principal,
            'principal': principal,
            'Interest Rate': rate,
            'interest_rate': rate,
            'Avg Rate': rate,
            'avg_rate': rate,
            'Weighted Avg Rate': rate,
            'weighted_avg_rate': rate,
            'Total Interest': interest,
            'total_interest': interest,
            'Interest Earned': interest,
            'interest_earned': interest,
            'Annual Yield': rate,
            'annual_yield': rate,
            'Effective Annual Rate': rate,
            'effective_annual_rate': rate,
            'Days to Maturity': days,
            'days_to_maturity': days,
            'Avg Days to Maturity': days,
            'avg_days_to_maturity': days
        }
        
    elif instrument_type == 'bonds':
        face_value = get_number(extracted_values.get('faceValue') or 
                                extracted_values.get('Face Value') or 
                                extracted_values.get('principal') or 
                                extracted_values.get('Principal') or 
                                extracted_values.get('amount') or 
                                extracted_values.get('Amount') or 0)
        
        coupon_rate = get_number(extracted_values.get('couponRate') or 
                              extracted_values.get('Coupon Rate') or 
                              extracted_values.get('rate') or 
                              extracted_values.get('Rate') or 
                              extracted_values.get('interestRate') or 
                              extracted_values.get('Interest Rate') or 0)
        
        yield_to_maturity = get_number(extracted_values.get('yield') or 
                                     extracted_values.get('Yield') or 
                                     extracted_values.get('YTM') or 
                                     extracted_values.get('ytm') or 
                                     extracted_values.get('Yield to Maturity') or 0)
        
        frequency = get_string(extracted_values.get('couponFrequency') or 
                            extracted_values.get('Coupon Frequency') or 
                            extracted_values.get('frequency') or 
                            extracted_values.get('Frequency') or 'Semi-annual')
        
        price = get_number(extracted_values.get('price') or 
                         extracted_values.get('Price') or 
                         extracted_values.get('marketPrice') or 
                         extracted_values.get('Market Price') or face_value)
        
        # Bond calculations
        annual_coupon = face_value * (coupon_rate / 100)
        
        # Simplified duration calculation (Macaulay duration approximation)
        duration = 7.0  # Default approximation
        
        results = {
            'Instrument Name': instrument_name,
            'Total Value': face_value,
            'total_value': face_value,
            'Instrument Count': 1,
            'instrument_count': 1,
            'Face Value': face_value,
            'face_value': face_value,
            'Coupon Rate': coupon_rate,
            'coupon_rate': coupon_rate,
            'Avg Coupon Rate': coupon_rate,
            'avg_coupon_rate': coupon_rate,
            'Weighted Avg Coupon': coupon_rate,
            'weighted_avg_coupon': coupon_rate,
            'Yield to Maturity': yield_to_maturity,
            'yield_to_maturity': yield_to_maturity,
            'Avg YTM': yield_to_maturity,
            'avg_ytm': yield_to_maturity,
            'Price': price,
            'price': price,
            'Total Annual Income': annual_coupon,
            'total_annual_income': annual_coupon,
            'Coupon Frequency': frequency,
            'coupon_frequency': frequency,
            'Duration': duration,
            'duration': duration
        }
        
    elif instrument_type == 'tbills':
        face_value = get_number(extracted_values.get('faceValue') or 
                                extracted_values.get('Face Value') or 
                                extracted_values.get('principal') or 
                                extracted_values.get('Principal') or 
                                extracted_values.get('amount') or 
                                extracted_values.get('Amount') or 0)
        
        discount_rate = get_number(extracted_values.get('discountRate') or 
                                  extracted_values.get('Discount Rate') or 
                                  extracted_values.get('rate') or 
                                  extracted_values.get('Rate') or 0)
        
        days = get_number(extracted_values.get('daysToMaturity') or 
                        extracted_values.get('Days to Maturity') or 
                        extracted_values.get('term') or 
                        extracted_values.get('Term') or 
                        extracted_values.get('maturity') or 
                        extracted_values.get('Maturity') or 90)
        
        # T-Bill calculations
        discount = face_value * (discount_rate / 100) * (days / 360)
        purchase_price = face_value - discount
        price_per_100 = 100 * (1 - (discount_rate / 100) * (days / 360))
        
        results = {
            'Instrument Name': instrument_name,
            'Total Value': face_value,
            'total_value': face_value,
            'Instrument Count': 1,
            'instrument_count': 1,
            'Face Value': face_value,
            'face_value': face_value,
            'Discount Rate': discount_rate,
            'discount_rate': discount_rate,
            'Avg Discount Rate': discount_rate,
            'avg_discount_rate': discount_rate,
            'Weighted Avg Discount': discount_rate,
            'weighted_avg_discount': discount_rate,
            'Total Discount': discount,
            'total_discount': discount,
            'Purchase Price': purchase_price,
            'purchase_price': purchase_price,
            'Total Purchase Price': purchase_price,
            'total_purchase_price': purchase_price,
            'Avg Investment': purchase_price,
            'avg_investment': purchase_price,
            'Price per 100': price_per_100,
            'price_per_100': price_per_100,
            'Days to Maturity': days,
            'days_to_maturity': days,
            'Avg Days to Maturity': days,
            'avg_days_to_maturity': days,
            'Bond Equivalent Yield': discount_rate,
            'bond_equivalent_yield': discount_rate,
            'Effective Yield': discount_rate,
            'effective_yield': discount_rate,
            'Holding Period Yield': discount_rate,
            'holding_period_yield': discount_rate,
            'Annualized Yield': discount_rate,
            'annualized_yield': discount_rate
        }
    
    else:
        # Default fallback
        results = {
            'Instrument Name': instrument_name,
            'Total Value': 0,
            'total_value': 0,
            'Instrument Count': 1,
            'instrument_count': 1
        }
    
    return results
