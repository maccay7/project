from typing import Any, Dict, Optional
from decimal import Decimal, ROUND_HALF_UP


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:
        return None
    return f


def _round_half_up(value: float, decimals: int) -> float:
    # Financial rounding: 100.125 -> 100.13, not banker's 100.12.
    quantizer = Decimal(1).scaleb(-decimals)
    return float(Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP))


def round_percentage(value: Any, decimal_places: int = 4) -> Optional[float]:
    f = _to_float(value)
    if f is None:
        return None
    return _round_half_up(f, decimal_places)


def round_money(value: Any) -> Optional[float]:
    f = _to_float(value)
    if f is None:
        return None
    return _round_half_up(f, 2)


def round_value(value: Any, decimal_places: int = 4) -> Optional[float]:
    f = _to_float(value)
    if f is None:
        return None
    return _round_half_up(f, decimal_places)


def round_calculation_result(result: Any, field_type: str = "default") -> Optional[float]:
    if result is None or result == "":
        return None
    if field_type == "percentage":
        return round_percentage(result)
    if field_type == "money":
        return round_money(result)
    return round_value(result)


def round_dict_values(data_dict: Dict[str, Any],
                      field_mappings: Dict[str, str]) -> Dict[str, Optional[float]]:
    return {
        key: round_calculation_result(value, field_mappings.get(key, "default"))
        for key, value in data_dict.items()
    }


PERCENTAGE_FIELDS = {
    "coupon_rate", "yield", "yield_to_maturity", "yield_to_call", "yield_to_worst",
    "current_yield", "effective_annual_yield", "bank_discount_yield",
    "bond_equivalent_yield", "holding_period_yield", "money_market_yield",
    "discount_rate", "annual_discount_rate", "nominal_annual_rate",
    "annual_percentage_yield", "benchmark_spread", "g_spread", "i_spread",
    "z_spread", "credit_spread", "real_yield", "nominal_yield",
    "interest_rate", "rate", "percentage_return", "weighted_avg_rate",
    "weighted_avg_coupon", "weighted_avg_discount", "portfolio_avg_rate",
}

MONEY_FIELDS = {
    "face_value", "principal", "present_value", "fair_value", "market_value",
    "purchase_price", "settlement_amount", "redemption_value", "maturity_value",
    "net_proceeds", "gross_proceeds", "investment_cost", "clean_price",
    "dirty_price", "coupon_payment", "accrued_interest", "settlement_value",
    "total_value", "amount", "price", "discount_amount", "interest_earned",
    "investment_return", "net_investment", "gross_investment", "gain_loss",
    "capital_gain_loss", "coupon_income", "unrealized_gain_loss",
    "realized_gain_loss",
}


def auto_round_by_field_name(field_name: str, value: Any) -> Optional[float]:
    if value is None:
        return None
    field_lower = field_name.lower()

    if any(k in field_lower for k in ("rate", "yield", "spread", "percent", "return")):
        return round_percentage(value)

    if any(k in field_lower for k in (
        "value", "price", "amount", "cost", "proceeds", "interest",
        "payment", "discount", "gain", "loss", "income",
        "investment", "principal", "face",
    )):
        return round_money(value)

    return round_value(value, 4)