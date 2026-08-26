"""
Calculation Dependency Validation Engine

This module provides dependency validation for all financial calculations,
ensuring that required fields are present before attempting calculations.
No mock or fallback data is used - missing dependencies are clearly reported.
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class CalculationStatus(Enum):
    """Status of a calculation validation."""
    CAN_CALCULATE = "can_calculate"
    MISSING_DEPENDENCIES = "missing_dependencies"
    INVALID_VALUES = "invalid_values"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class DependencyValidation:
    """Result of dependency validation for a calculation."""
    calculation_name: str
    status: CalculationStatus
    can_calculate: bool
    missing_fields: List[str]
    invalid_fields: List[Tuple[str, str]]  # (field_name, reason)
    warnings: List[str]
    required_fields: List[str]
    optional_fields: List[str]


class CalculationDependencyEngine:
    """
    Calculation dependency validation engine.
    
    This engine:
    - Defines dependencies for all financial calculations
    - Validates that required fields exist before calculation
    - Provides clear error messages for missing dependencies
    - Never uses mock or fallback data
    - Supports all three instrument types
    """
    
    def __init__(self):
        # Define calculation dependencies for Money Market
        self.money_market_dependencies = {
            'term_days_to_maturity': {
                'required': ['settlement_date', 'maturity_date'],
                'optional': [],
                'formula': 'Days = Maturity Date - Settlement Date',
                'description': 'Calculate days between settlement and maturity'
            },
            'simple_interest': {
                'required': ['principal', 'interest_rate', 'days_to_maturity', 'day_count_convention'],
                'optional': [],
                'formula': 'Interest = Principal × Rate × Days / Day Basis',
                'description': 'Simple interest calculation'
            },
            'maturity_total_value': {
                'required': ['principal', 'interest_earned'],
                'optional': [],
                'formula': 'Total Value = Principal + Interest',
                'description': 'Total value at maturity'
            },
            'interest_rate_from_interest': {
                'required': ['interest_earned', 'principal', 'days_to_maturity', 'day_count_convention'],
                'optional': [],
                'formula': 'Rate = Interest / Principal × Day Basis / Days',
                'description': 'Calculate rate from interest earned'
            },
            'discount_amount': {
                'required': ['face_value', 'purchase_price'],
                'optional': [],
                'formula': 'Discount = Face Value - Purchase Price',
                'description': 'Discount amount calculation'
            },
            'discount_rate': {
                'required': ['face_value', 'purchase_price', 'days_to_maturity', 'day_count_convention'],
                'optional': [],
                'formula': 'Discount Yield = (Face Value - Purchase Price) / Face Value × Day Basis / Days',
                'description': 'Discount rate/yield calculation'
            },
            'investment_yield': {
                'required': ['face_value', 'purchase_price', 'days_to_maturity', 'day_count_convention'],
                'optional': [],
                'formula': 'Investment Yield = (Face Value - Purchase Price) / Purchase Price × Day Basis / Days',
                'description': 'Investment yield calculation'
            },
            'effective_annual_yield': {
                'required': ['investment_yield', 'compounding_frequency'],
                'optional': [],
                'formula': 'Effective Yield = (1 + r/n)^n - 1',
                'description': 'Effective annual yield with compounding'
            },
            'present_value': {
                'required': ['future_value', 'rate', 'days_to_maturity', 'day_count_convention'],
                'optional': [],
                'formula': 'PV = FV / (1 + Rate × Days / Day Basis)',
                'description': 'Present value calculation'
            },
            'accrued_interest': {
                'required': ['face_value', 'interest_rate', 'accrued_days', 'day_count_convention'],
                'optional': [],
                'formula': 'Accrued Interest = Face × Rate × Accrued Days / Day Basis',
                'description': 'Accrued interest calculation'
            }
        }
        
        # Define calculation dependencies for T-Bills
        self.tbills_dependencies = {
            'days_to_maturity': {
                'required': ['settlement_date', 'maturity_date'],
                'optional': [],
                'formula': 'Days = Maturity Date - Settlement Date',
                'description': 'Calculate days between settlement and maturity'
            },
            'price_per_100': {
                'required': ['discount_rate', 'days_to_maturity', 'day_count_convention'],
                'optional': [],
                'formula': 'Price = 100 × (1 - Discount Rate × Days / Day Basis)',
                'description': 'Price per 100 face value'
            },
            'purchase_price': {
                'required': ['face_value', 'price_per_100'],
                'optional': [],
                'formula': 'Purchase Price = Face Value / 100 × Price per 100',
                'description': 'Total purchase price'
            },
            'discount_amount': {
                'required': ['face_value', 'purchase_price'],
                'optional': [],
                'formula': 'Discount = Face Value - Purchase Price',
                'description': 'Discount amount'
            },
            'discount_rate': {
                'required': ['face_value', 'purchase_price', 'days_to_maturity'],
                'optional': [],
                'formula': 'Discount Rate = ((Face Value - Purchase Price) / Face Value) × (360 / Days)',
                'description': 'Discount rate calculation'
            },
            'investment_yield': {
                'required': ['face_value', 'purchase_price', 'days_to_maturity'],
                'optional': [],
                'formula': 'Investment Yield = ((Face Value - Purchase Price) / Purchase Price) × (365 / Days)',
                'description': 'Investment yield (coupon-equivalent yield)'
            },
            'profit_return': {
                'required': ['face_value', 'purchase_price'],
                'optional': [],
                'formula': 'Profit = Face Value - Purchase Price',
                'description': 'Profit at maturity'
            },
            'return_percentage': {
                'required': ['profit', 'purchase_price'],
                'optional': [],
                'formula': 'Return % = Profit / Purchase Price × 100',
                'description': 'Return as percentage'
            },
            'maturity_value': {
                'required': ['face_value'],
                'optional': [],
                'formula': 'Maturity Value = Face Value',
                'description': 'Value at maturity'
            },
            'present_value': {
                'required': ['face_value', 'discount_rate', 'days_to_maturity', 'day_count_convention'],
                'optional': [],
                'formula': 'PV calculation using applicable T-Bill pricing formula',
                'description': 'Present value using discount rate'
            }
        }
        
        # Define calculation dependencies for Bonds
        self.bonds_dependencies = {
            'term_to_maturity': {
                'required': ['settlement_date', 'maturity_date'],
                'optional': [],
                'formula': 'Term = Maturity Date - Settlement Date',
                'description': 'Term to maturity in years/days'
            },
            'annual_coupon': {
                'required': ['face_value', 'coupon_rate'],
                'optional': [],
                'formula': 'Annual Coupon = Face Value × Coupon Rate',
                'description': 'Annual coupon payment'
            },
            'coupon_payment': {
                'required': ['face_value', 'coupon_rate', 'coupon_frequency'],
                'optional': [],
                'formula': 'Coupon Payment = Face Value × Coupon Rate / Frequency',
                'description': 'Per-period coupon payment'
            },
            'pv_coupons': {
                'required': ['coupon_payment', 'yield', 'coupon_frequency', 'remaining_periods'],
                'optional': [],
                'formula': 'PV Coupons = Σ [Coupon / (1 + Yield/Frequency)^t]',
                'description': 'Present value of coupon cash flows'
            },
            'pv_principal': {
                'required': ['face_value', 'yield', 'coupon_frequency', 'remaining_periods'],
                'optional': [],
                'formula': 'PV Principal = Face Value / (1 + Yield/Frequency)^n',
                'description': 'Present value of principal repayment'
            },
            'bond_price': {
                'required': ['coupon_payment', 'face_value', 'yield', 'coupon_frequency', 'remaining_periods'],
                'optional': [],
                'formula': 'Bond Price = Σ [Coupon / (1 + Yield/Frequency)^t] + Face Value / (1 + Yield/Frequency)^n',
                'description': 'Bond price calculation'
            },
            'clean_price': {
                'required': ['dirty_price', 'accrued_interest'],
                'optional': [],
                'formula': 'Clean Price = Dirty Price - Accrued Interest',
                'description': 'Clean price (without accrued interest)'
            },
            'dirty_price': {
                'required': ['clean_price', 'accrued_interest'],
                'optional': [],
                'formula': 'Dirty Price = Clean Price + Accrued Interest',
                'description': 'Dirty price (with accrued interest)'
            },
            'accrued_interest': {
                'required': ['coupon_payment', 'accrued_days', 'days_in_coupon_period'],
                'optional': [],
                'formula': 'Accrued Interest = Coupon Payment × Accrued Days / Coupon Period Days',
                'description': 'Accrued interest calculation'
            },
            'current_yield': {
                'required': ['annual_coupon', 'current_price'],
                'optional': [],
                'formula': 'Current Yield = Annual Coupon / Market Price',
                'description': 'Current yield calculation'
            },
            'yield_to_maturity': {
                'required': ['current_price', 'face_value', 'coupon_rate', 'coupon_frequency', 'remaining_periods'],
                'optional': [],
                'formula': 'Solve: Price = Σ [Coupon / (1 + YTM/Frequency)^t] + Face Value / (1 + YTM/Frequency)^n',
                'description': 'Yield to maturity (requires numerical solving)'
            },
            'macaulay_duration': {
                'required': ['coupon_cash_flows', 'principal_cash_flow', 'yield', 'periods', 'bond_price'],
                'optional': [],
                'formula': 'Macaulay Duration = Σ [t × PV(Cash Flow)] / Bond Price',
                'description': 'Macaulay duration calculation'
            },
            'modified_duration': {
                'required': ['macaulay_duration', 'yield', 'coupon_frequency'],
                'optional': [],
                'formula': 'Modified Duration = Macaulay Duration / (1 + YTM/Frequency)',
                'description': 'Modified duration calculation'
            },
            'effective_duration': {
                'required': ['price_lower_yield', 'price_higher_yield', 'current_price', 'yield_change'],
                'optional': [],
                'formula': 'Effective Duration = (P- - P+) / (2 × P0 × Δy)',
                'description': 'Effective duration calculation'
            },
            'convexity': {
                'required': ['price_lower_yield', 'price_higher_yield', 'current_price', 'yield_change'],
                'optional': [],
                'formula': 'Convexity = (P+ + P- - 2P0) / (P0 × Δy²)',
                'description': 'Convexity calculation'
            },
            'dv01': {
                'required': ['bond_price', 'duration', 'yield'],
                'optional': [],
                'formula': 'DV01 = Price Value of a Basis Point',
                'description': 'Price value of a basis point'
            },
            'yield_spread': {
                'required': ['bond_yield', 'benchmark_yield'],
                'optional': [],
                'formula': 'Spread = Bond Yield - Benchmark Rate',
                'description': 'Yield spread over benchmark'
            },
            'market_value': {
                'required': ['face_value', 'price'],
                'optional': [],
                'formula': 'Market Value = Face Value × Price / 100',
                'description': 'Market value calculation'
            },
            'interest_income': {
                'required': ['coupon_payment', 'number_of_payments'],
                'optional': [],
                'formula': 'Interest Income = Coupon Payment × Number of Payments',
                'description': 'Total interest income'
            },
            'capital_gain_loss': {
                'required': ['current_value', 'purchase_cost'],
                'optional': [],
                'formula': 'Capital Gain/Loss = Current Value - Purchase Cost',
                'description': 'Capital gain or loss'
            },
            'total_return': {
                'required': ['interest_income', 'capital_gain_loss'],
                'optional': [],
                'formula': 'Total Return = Interest Income + Capital Gain/Loss',
                'description': 'Total return calculation'
            },
            'total_return_percentage': {
                'required': ['total_return', 'initial_investment'],
                'optional': [],
                'formula': 'Total Return % = Total Return / Initial Investment × 100',
                'description': 'Total return as percentage'
            }
        }
    
    def validate_calculation(self, calculation_name: str, 
                           available_fields: Dict[str, any],
                           instrument_type: str) -> DependencyValidation:
        """
        Validate if a calculation can be performed with available fields.
        
        Args:
            calculation_name: Name of the calculation to validate
            available_fields: Dictionary of available fields and their values
            instrument_type: Type of instrument ('money-market', 'tbills', 'bonds')
            
        Returns:
            DependencyValidation object with validation result
        """
        # Get dependencies for the instrument type
        if instrument_type == 'money-market':
            dependencies = self.money_market_dependencies
        elif instrument_type == 'tbills':
            dependencies = self.tbills_dependencies
        elif instrument_type == 'bonds':
            dependencies = self.bonds_dependencies
        else:
            return DependencyValidation(
                calculation_name=calculation_name,
                status=CalculationStatus.INSUFFICIENT_DATA,
                can_calculate=False,
                missing_fields=[],
                invalid_fields=[],
                warnings=[f"Unknown instrument type: {instrument_type}"],
                required_fields=[],
                optional_fields=[]
            )
        
        # Get calculation dependencies
        calc_deps = dependencies.get(calculation_name)
        if not calc_deps:
            return DependencyValidation(
                calculation_name=calculation_name,
                status=CalculationStatus.INSUFFICIENT_DATA,
                can_calculate=False,
                missing_fields=[],
                invalid_fields=[],
                warnings=[f"Unknown calculation: {calculation_name}"],
                required_fields=[],
                optional_fields=[]
            )
        
        required_fields = calc_deps['required']
        optional_fields = calc_deps['optional']
        
        # Check for missing required fields
        missing_fields = []
        for field in required_fields:
            if field not in available_fields or available_fields[field] is None or available_fields[field] == '':
                missing_fields.append(field)
        
        # Check for invalid values
        invalid_fields = []
        for field in required_fields:
            if field in available_fields:
                value = available_fields[field]
                if value is not None and value != '':
                    # Validate numeric fields
                    if field in ['principal', 'face_value', 'purchase_price', 'interest_rate', 
                               'coupon_rate', 'discount_rate', 'yield', 'days_to_maturity',
                               'remaining_periods', 'coupon_frequency', 'price']:
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            invalid_fields.append((field, f"Invalid numeric value: {value}"))
                    
                    # Validate date fields
                    if field in ['settlement_date', 'maturity_date', 'issue_date']:
                        if not isinstance(value, str) or len(value) < 8:
                            invalid_fields.append((field, f"Invalid date format: {value}"))
        
        # Determine status
        if missing_fields:
            status = CalculationStatus.MISSING_DEPENDENCIES
            can_calculate = False
        elif invalid_fields:
            status = CalculationStatus.INVALID_VALUES
            can_calculate = False
        else:
            status = CalculationStatus.CAN_CALCULATE
            can_calculate = True
        
        # Generate warnings
        warnings = []
        if can_calculate:
            # Check if optional fields are missing
            for field in optional_fields:
                if field not in available_fields or available_fields[field] is None:
                    warnings.append(f"Optional field '{field}' is missing - using default behavior if applicable")
        
        return DependencyValidation(
            calculation_name=calculation_name,
            status=status,
            can_calculate=can_calculate,
            missing_fields=missing_fields,
            invalid_fields=invalid_fields,
            warnings=warnings,
            required_fields=required_fields,
            optional_fields=optional_fields
        )
    
    def validate_all_calculations(self, available_fields: Dict[str, any],
                                 instrument_type: str) -> Dict[str, DependencyValidation]:
        """
        Validate all calculations for an instrument type.
        
        Args:
            available_fields: Dictionary of available fields and their values
            instrument_type: Type of instrument
            
        Returns:
            Dictionary mapping calculation names to validation results
        """
        # Get all calculation names for the instrument type
        if instrument_type == 'money-market':
            calculation_names = list(self.money_market_dependencies.keys())
        elif instrument_type == 'tbills':
            calculation_names = list(self.tbills_dependencies.keys())
        elif instrument_type == 'bonds':
            calculation_names = list(self.bonds_dependencies.keys())
        else:
            return {}
        
        results = {}
        for calc_name in calculation_names:
            results[calc_name] = self.validate_calculation(
                calc_name, available_fields, instrument_type
            )
        
        return results
    
    def get_calculation_formula(self, calculation_name: str, instrument_type: str) -> Optional[str]:
        """
        Get the formula for a calculation.
        
        Args:
            calculation_name: Name of the calculation
            instrument_type: Type of instrument
            
        Returns:
            Formula string or None if not found
        """
        if instrument_type == 'money-market':
            dependencies = self.money_market_dependencies
        elif instrument_type == 'tbills':
            dependencies = self.tbills_dependencies
        elif instrument_type == 'bonds':
            dependencies = self.bonds_dependencies
        else:
            return None
        
        calc_deps = dependencies.get(calculation_name)
        return calc_deps.get('formula') if calc_deps else None
    
    def get_calculation_description(self, calculation_name: str, instrument_type: str) -> Optional[str]:
        """
        Get the description for a calculation.
        
        Args:
            calculation_name: Name of the calculation
            instrument_type: Type of instrument
            
        Returns:
            Description string or None if not found
        """
        if instrument_type == 'money-market':
            dependencies = self.money_market_dependencies
        elif instrument_type == 'tbills':
            dependencies = self.tbills_dependencies
        elif instrument_type == 'bonds':
            dependencies = self.bonds_dependencies
        else:
            return None
        
        calc_deps = dependencies.get(calculation_name)
        return calc_deps.get('description') if calc_deps else None
    
    def get_available_calculations(self, available_fields: Dict[str, any],
                                  instrument_type: str) -> List[str]:
        """
        Get list of calculations that can be performed with available fields.
        
        Args:
            available_fields: Dictionary of available fields and their values
            instrument_type: Type of instrument
            
        Returns:
            List of calculation names that can be calculated
        """
        validations = self.validate_all_calculations(available_fields, instrument_type)
        available = [
            calc_name for calc_name, validation in validations.items()
            if validation.can_calculate
        ]
        return available
    
    def get_missing_fields_message(self, validation: DependencyValidation) -> str:
        """
        Generate a user-friendly error message for missing dependencies.
        
        Args:
            validation: DependencyValidation result
            
        Returns:
            User-friendly error message
        """
        if validation.can_calculate:
            return f"Can calculate {validation.calculation_name}"
        
        messages = []
        
        if validation.missing_fields:
            missing_str = ", ".join(validation.missing_fields)
            messages.append(f"Cannot calculate {validation.calculation_name}: missing required fields [{missing_str}]")
        
        if validation.invalid_fields:
            invalid_str = ", ".join([f"{field} ({reason})" for field, reason in validation.invalid_fields])
            messages.append(f"Invalid fields: {invalid_str}")
        
        return " ".join(messages) if messages else f"Cannot calculate {validation.calculation_name}"


def create_calculation_dependency_engine() -> CalculationDependencyEngine:
    """Factory function to create a calculation dependency engine."""
    return CalculationDependencyEngine()
