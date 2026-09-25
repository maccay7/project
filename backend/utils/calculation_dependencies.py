"""
Calculation Dependency Validation Engine

Validates that required fields are present before attempting calculations.
No mock or fallback data is used - missing dependencies are clearly reported.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class CalculationStatus(Enum):
    CAN_CALCULATE = "can_calculate"
    MISSING_DEPENDENCIES = "missing_dependencies"
    INVALID_VALUES = "invalid_values"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class DependencyValidation:
    calculation_name: str
    status: CalculationStatus
    can_calculate: bool
    missing_fields: List[str]
    invalid_fields: List[Tuple[str, str]]
    warnings: List[str]
    required_fields: List[str]
    optional_fields: List[str]


# -----------------------------------------------------------------------------
# Frequency labels → integer (payments per year)
# -----------------------------------------------------------------------------
TEXT_FREQUENCY_VALUES = {
    "annual": 1, "annually": 1, "yearly": 1, "1": 1,
    "semi-annual": 2, "semiannual": 2, "semi annual": 2,
    "semi annually": 2, "semiannually": 2, "2": 2,
    "quarterly": 4, "quarter": 4, "4": 4,
    "monthly": 12, "month": 12, "12": 12,
    "weekly": 52, "52": 52,
    "daily": 365, "365": 365,
}

NUMERIC_FIELDS = {
    "principal", "face_value", "purchase_price", "interest_rate",
    "coupon_rate", "discount_rate", "yield", "days_to_maturity",
    "remaining_periods", "price", "years_to_maturity",
    "market_price", "current_price", "call_price", "put_price",
}


def parse_frequency(value: Any) -> Optional[int]:
    """Convert 'semi-annual' / 2 / '2' to an int. Returns None if unknown."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            n = int(value)
            return n if n > 0 else None
        except (ValueError, TypeError):
            return None
    if isinstance(value, str):
        key = value.strip().lower()
        if key in TEXT_FREQUENCY_VALUES:
            return TEXT_FREQUENCY_VALUES[key]
        try:
            n = int(float(key))
            return n if n > 0 else None
        except ValueError:
            return None
    return None


class CalculationDependencyEngine:
    """Defines and validates calculation dependencies for every instrument type."""

    def __init__(self):
        self.money_market_dependencies = {
            "term_days_to_maturity": {
                "required": ["settlement_date", "maturity_date"],
                "optional": [],
                "formula": "Days = Maturity Date - Settlement Date",
                "description": "Days between settlement and maturity",
            },
            "simple_interest": {
                "required": ["principal", "interest_rate", "days_to_maturity",
                             "day_count_convention"],
                "optional": [],
                "formula": "Interest = Principal x Rate x Days / Day Basis",
                "description": "Simple interest calculation",
            },
            "maturity_total_value": {
                "required": ["principal", "interest_earned"],
                "optional": [],
                "formula": "Total Value = Principal + Interest",
                "description": "Total value at maturity",
            },
            "discount_amount": {
                "required": ["face_value", "purchase_price"],
                "optional": [],
                "formula": "Discount = Face Value - Purchase Price",
                "description": "Discount amount",
            },
            "discount_rate": {
                "required": ["face_value", "purchase_price", "days_to_maturity",
                             "day_count_convention"],
                "optional": [],
                "formula": "Discount Yield = (FV - PP) / FV x Day Basis / Days",
                "description": "Discount yield",
            },
            "investment_yield": {
                "required": ["face_value", "purchase_price", "days_to_maturity",
                             "day_count_convention"],
                "optional": [],
                "formula": "Investment Yield = (FV - PP) / PP x Day Basis / Days",
                "description": "Investment yield",
            },
            "effective_annual_yield": {
                "required": ["investment_yield", "compounding_frequency"],
                "optional": [],
                "formula": "Effective Yield = (1 + r/n)^n - 1",
                "description": "Effective annual yield",
            },
            "present_value": {
                "required": ["future_value", "rate", "days_to_maturity",
                             "day_count_convention"],
                "optional": [],
                "formula": "PV = FV / (1 + Rate x Days / Day Basis)",
                "description": "Present value",
            },
            "accrued_interest": {
                "required": ["face_value", "interest_rate", "accrued_days",
                             "day_count_convention"],
                "optional": [],
                "formula": "Accrued Interest = Face x Rate x Accrued Days / Day Basis",
                "description": "Accrued interest",
            },
        }

        self.tbills_dependencies = {
            "days_to_maturity": {
                "required": ["settlement_date", "maturity_date"],
                "optional": [],
                "formula": "Days = Maturity Date - Settlement Date",
                "description": "Days between settlement and maturity",
            },
            "price_per_100": {
                "required": ["discount_rate", "days_to_maturity",
                             "day_count_convention"],
                "optional": [],
                "formula": "Price = 100 x (1 - Discount Rate x Days / Day Basis)",
                "description": "Price per 100 face value",
            },
            "purchase_price": {
                "required": ["face_value", "price_per_100"],
                "optional": [],
                "formula": "Purchase Price = Face Value / 100 x Price per 100",
                "description": "Total purchase price",
            },
            "discount_amount": {
                "required": ["face_value", "purchase_price"],
                "optional": [],
                "formula": "Discount = Face Value - Purchase Price",
                "description": "Discount amount",
            },
            "discount_rate": {
                "required": ["face_value", "purchase_price", "days_to_maturity"],
                "optional": [],
                "formula": "Discount Rate = ((FV - PP) / FV) x (360 / Days)",
                "description": "Discount rate",
            },
            "investment_yield": {
                "required": ["face_value", "purchase_price", "days_to_maturity"],
                "optional": [],
                "formula": "Investment Yield = ((FV - PP) / PP) x (365 / Days)",
                "description": "Investment yield",
            },
            "profit_return": {
                "required": ["face_value", "purchase_price"],
                "optional": [],
                "formula": "Profit = Face Value - Purchase Price",
                "description": "Profit at maturity",
            },
            "maturity_value": {
                "required": ["face_value"],
                "optional": [],
                "formula": "Maturity Value = Face Value",
                "description": "Value at maturity",
            },
            "present_value": {
                "required": ["face_value", "discount_rate", "days_to_maturity",
                             "day_count_convention"],
                "optional": [],
                "formula": "PV = FV x (1 - discount x days / basis)",
                "description": "Present value using discount rate",
            },
        }

        self.bonds_dependencies = {
            "term_to_maturity": {
                "required": ["settlement_date", "maturity_date"],
                "optional": [],
                "formula": "Term = Maturity Date - Settlement Date",
                "description": "Term to maturity",
            },
            "annual_coupon": {
                "required": ["face_value", "coupon_rate"],
                "optional": [],
                "formula": "Annual Coupon = Face Value x Coupon Rate",
                "description": "Annual coupon",
            },
            "coupon_payment": {
                "required": ["face_value", "coupon_rate", "coupon_frequency"],
                "optional": [],
                "formula": "Coupon = Face Value x Coupon Rate / Frequency",
                "description": "Per-period coupon",
            },
            "bond_price": {
                "required": ["face_value", "coupon_rate", "yield", "coupon_frequency",
                             "years_to_maturity"],
                "optional": [],
                "formula": "Price = PV(coupons) + PV(face)",
                "description": "Bond price",
            },
            "accrued_interest": {
                "required": ["coupon_payment", "accrued_days",
                             "days_in_coupon_period"],
                "optional": [],
                "formula": "AI = Coupon x Accrued Days / Period Days",
                "description": "Accrued interest",
            },
            "current_yield": {
                "required": ["annual_coupon", "current_price"],
                "optional": [],
                "formula": "Current Yield = Annual Coupon / Price",
                "description": "Current yield",
            },
            "yield_to_maturity": {
                "required": ["current_price", "face_value", "coupon_rate",
                             "coupon_frequency", "years_to_maturity"],
                "optional": [],
                "formula": "Solve for r where Price = PV(coupons) + PV(face)",
                "description": "Yield to maturity",
            },
            "macaulay_duration": {
                "required": ["face_value", "coupon_rate", "yield",
                             "coupon_frequency", "years_to_maturity"],
                "optional": [],
                "formula": "Sum(t * PV(CF)) / Price",
                "description": "Macaulay duration",
            },
            "modified_duration": {
                "required": ["macaulay_duration", "yield", "coupon_frequency"],
                "optional": [],
                "formula": "Macaulay / (1 + YTM / frequency)",
                "description": "Modified duration",
            },
            "convexity": {
                "required": ["face_value", "coupon_rate", "yield",
                             "coupon_frequency", "years_to_maturity"],
                "optional": [],
                "formula": "Sum(t(t+1) PV(CF)) / (Price (1+r)^2)",
                "description": "Convexity",
            },
            "dv01": {
                "required": ["bond_price", "duration"],
                "optional": [],
                "formula": "DV01 = Price x ModDur x 0.0001",
                "description": "Price value of a basis point",
            },
            "yield_spread": {
                "required": ["bond_yield", "benchmark_yield"],
                "optional": [],
                "formula": "Spread = Bond Yield - Benchmark Rate",
                "description": "Yield spread over benchmark",
            },
            "market_value": {
                "required": ["face_value", "price"],
                "optional": [],
                "formula": "Market Value = Face Value x Price / 100",
                "description": "Market value",
            },
            "interest_income": {
                "required": ["coupon_payment", "number_of_payments"],
                "optional": [],
                "formula": "Interest Income = Coupon x N",
                "description": "Total interest income",
            },
            "capital_gain_loss": {
                "required": ["current_value", "purchase_cost"],
                "optional": [],
                "formula": "Capital G/L = Current Value - Purchase Cost",
                "description": "Capital gain or loss",
            },
            "total_return": {
                "required": ["interest_income", "capital_gain_loss"],
                "optional": [],
                "formula": "Total Return = Interest Income + Capital G/L",
                "description": "Total return",
            },
        }

    def _deps_for(self, instrument_type: str) -> Optional[Dict[str, Any]]:
        if instrument_type == "money-market":
            return self.money_market_dependencies
        if instrument_type == "tbills":
            return self.tbills_dependencies
        if instrument_type == "bonds":
            return self.bonds_dependencies
        return None

    def validate_calculation(self, calculation_name: str,
                             available_fields: Dict[str, Any],
                             instrument_type: str) -> DependencyValidation:
        dependencies = self._deps_for(instrument_type)
        if dependencies is None:
            return DependencyValidation(
                calculation_name=calculation_name,
                status=CalculationStatus.INSUFFICIENT_DATA,
                can_calculate=False,
                missing_fields=[],
                invalid_fields=[],
                warnings=[f"Unknown instrument type: {instrument_type}"],
                required_fields=[],
                optional_fields=[],
            )

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
                optional_fields=[],
            )

        required_fields = calc_deps["required"]
        optional_fields = calc_deps["optional"]

        missing_fields: List[str] = []
        for field in required_fields:
            if field not in available_fields:
                missing_fields.append(field)
            elif available_fields[field] is None or available_fields[field] == "":
                missing_fields.append(field)

        invalid_fields: List[Tuple[str, str]] = []
        for field in required_fields:
            if field not in available_fields:
                continue
            value = available_fields[field]
            if value is None or value == "":
                continue

            if field == "coupon_frequency":
                if isinstance(value, str):
                    if value.strip().lower() not in TEXT_FREQUENCY_VALUES:
                        invalid_fields.append((field, f"Unknown frequency label: {value}"))
                else:
                    try:
                        if int(value) <= 0:
                            invalid_fields.append((field, f"Frequency must be > 0: {value}"))
                    except (ValueError, TypeError):
                        invalid_fields.append((field, f"Invalid frequency: {value}"))
            elif field in NUMERIC_FIELDS:
                try:
                    float(value)
                except (ValueError, TypeError):
                    invalid_fields.append((field, f"Invalid numeric value: {value}"))
            elif field in {"settlement_date", "maturity_date", "issue_date",
                           "valuation_date", "call_date", "put_date"}:
                if not isinstance(value, str) or len(value.strip()) < 8:
                    invalid_fields.append((field, f"Invalid date format: {value}"))

        if missing_fields:
            status = CalculationStatus.MISSING_DEPENDENCIES
            can_calculate = False
        elif invalid_fields:
            status = CalculationStatus.INVALID_VALUES
            can_calculate = False
        else:
            status = CalculationStatus.CAN_CALCULATE
            can_calculate = True

        warnings: List[str] = []
        if can_calculate:
            for field in optional_fields:
                if field not in available_fields or available_fields[field] is None:
                    warnings.append(f"Optional field '{field}' is missing")

        return DependencyValidation(
            calculation_name=calculation_name,
            status=status,
            can_calculate=can_calculate,
            missing_fields=missing_fields,
            invalid_fields=invalid_fields,
            warnings=warnings,
            required_fields=required_fields,
            optional_fields=optional_fields,
        )

    def validate_all_calculations(self, available_fields: Dict[str, Any],
                                  instrument_type: str) -> Dict[str, DependencyValidation]:
        dependencies = self._deps_for(instrument_type)
        if not dependencies:
            return {}
        return {
            name: self.validate_calculation(name, available_fields, instrument_type)
            for name in dependencies
        }

    def get_calculation_formula(self, calculation_name: str,
                                instrument_type: str) -> Optional[str]:
        dependencies = self._deps_for(instrument_type)
        if not dependencies:
            return None
        calc_deps = dependencies.get(calculation_name)
        return calc_deps.get("formula") if calc_deps else None

    def get_calculation_description(self, calculation_name: str,
                                    instrument_type: str) -> Optional[str]:
        dependencies = self._deps_for(instrument_type)
        if not dependencies:
            return None
        calc_deps = dependencies.get(calculation_name)
        return calc_deps.get("description") if calc_deps else None

    def get_available_calculations(self, available_fields: Dict[str, Any],
                                   instrument_type: str) -> List[str]:
        validations = self.validate_all_calculations(available_fields, instrument_type)
        return [name for name, v in validations.items() if v.can_calculate]

    def get_missing_fields_message(self, validation: DependencyValidation) -> str:
        if validation.can_calculate:
            return f"Can calculate {validation.calculation_name}"
        messages = []
        if validation.missing_fields:
            messages.append(
                f"Cannot calculate {validation.calculation_name}: "
                f"missing required fields [{', '.join(validation.missing_fields)}]"
            )
        if validation.invalid_fields:
            invalid_str = ", ".join(f"{f} ({r})" for f, r in validation.invalid_fields)
            messages.append(f"Invalid fields: {invalid_str}")
        return " ".join(messages) if messages else \
               f"Cannot calculate {validation.calculation_name}"


def create_calculation_dependency_engine() -> CalculationDependencyEngine:
    return CalculationDependencyEngine()