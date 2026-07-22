"""
Rounding utility for financial calculations.

Rounding rules:
- Percentages: Round to nearest whole number (0 decimal places)
- Money/Amounts: Round to 2 decimal places
- Other values: Round to 2 decimal places
"""

def round_percentage(value):
    """
    Round percentage values to nearest whole number.
    
    Args:
        value: The percentage value to round
        
    Returns:
        Rounded percentage as integer (whole number)
    """
    if value is None or value == '':
        return 0
    try:
        return int(round(float(value)))
    except (ValueError, TypeError):
        return 0


def round_money(value):
    """
    Round money/amount values to 2 decimal places.
    
    Args:
        value: The monetary value to round
        
    Returns:
        Rounded monetary value with 2 decimal places
    """
    if value is None or value == '':
        return 0.00
    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return 0.00


def round_value(value, decimal_places=2):
    """
    Round any value to specified decimal places (default 2).
    
    Args:
        value: The value to round
        decimal_places: Number of decimal places (default 2)
        
    Returns:
        Rounded value
    """
    if value is None or value == '':
        return round(0, decimal_places)
    try:
        return round(float(value), decimal_places)
    except (ValueError, TypeError):
        return round(0, decimal_places)


def round_calculation_result(result, field_type='default'):
    """
    Round calculation result based on field type.
    
    Args:
        result: The calculation result to round
        field_type: Type of field ('percentage', 'money', or 'default')
        
    Returns:
        Rounded result based on field type
    """
    if result is None or result == '':
        return 0
    
    if field_type == 'percentage':
        return round_percentage(result)
    elif field_type == 'money':
        return round_money(result)
    else:
        return round_value(result, 2)


def round_dict_values(data_dict, field_mappings):
    """
    Round all values in a dictionary based on field type mappings.
    
    Args:
        data_dict: Dictionary containing calculation results
        field_mappings: Dictionary mapping field names to their types
                       ('percentage', 'money', or 'default')
        
    Returns:
        Dictionary with rounded values
    """
    rounded_dict = {}
    for key, value in data_dict.items():
        field_type = field_mappings.get(key, 'default')
        rounded_dict[key] = round_calculation_result(value, field_type)
    return rounded_dict


# Common field type mappings for financial instruments
PERCENTAGE_FIELDS = {
    'coupon_rate', 'yield', 'yield_to_maturity', 'yield_to_call', 'yield_to_worst',
    'current_yield', 'effective_annual_yield', 'bank_discount_yield',
    'bond_equivalent_yield', 'holding_period_yield', 'money_market_yield',
    'discount_rate', 'annual_discount_rate', 'nominal_annual_rate',
    'annual_percentage_yield', 'benchmark_spread', 'g_spread', 'i_spread',
    'z_spread', 'credit_spread', 'real_yield', 'nominal_yield',
    'interest_rate', 'rate', 'percentage_return', 'weighted_avg_rate',
    'weighted_avg_coupon', 'weighted_avg_discount', 'portfolio_avg_rate'
}

MONEY_FIELDS = {
    'face_value', 'principal', 'present_value', 'fair_value', 'market_value',
    'purchase_price', 'settlement_amount', 'redemption_value', 'maturity_value',
    'net_proceeds', 'gross_proceeds', 'investment_cost', 'clean_price',
    'dirty_price', 'coupon_payment', 'accrued_interest', 'settlement_value',
    'total_value', 'amount', 'price', 'discount_amount', 'interest_earned',
    'investment_return', 'net_investment', 'gross_investment', 'gain_loss',
    'capital_gain_loss', 'coupon_income', 'unrealized_gain_loss',
    'realized_gain_loss'
}


def auto_round_by_field_name(field_name, value):
    """
    Automatically round value based on field name patterns.
    
    Args:
        field_name: Name of the field
        value: Value to round
        
    Returns:
        Rounded value based on field name pattern
    """
    field_lower = field_name.lower()
    
    # Check if field name suggests percentage
    if any(keyword in field_lower for keyword in ['rate', 'yield', 'spread', 'percent', 'return']):
        return round_percentage(value)
    
    # Check if field name suggests money
    elif any(keyword in field_lower for keyword in ['value', 'price', 'amount', 'cost', 'proceeds', 
                                                     'interest', 'payment', 'discount', 'gain', 'loss',
                                                     'income', 'investment', 'principal', 'face']):
        return round_money(value)
    
    # Default to 2 decimal places
    else:
        return round_value(value, 2)
