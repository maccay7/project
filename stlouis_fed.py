"""St. Louis Fed FRED API client for yield curve data."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests


class StLouisFedClient:
    """Client for fetching yield curve data from St. Louis Fed FRED API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize client with API key."""
        self.api_key = api_key or os.environ.get("STLOUIS_FED_API_KEY")
        if not self.api_key:
            raise ValueError("API key required. Set STLOUIS_FED_API_KEY environment variable or pass api_key parameter.")
        
        self.base_url = "https://api.stlouisfed.org/fred"
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to FRED API."""
        params["api_key"] = self.api_key
        params["file_type"] = "json"
        params["limit"] = 100  # Limit to recent observations
        
        try:
            response = self.session.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"FRED API request failed: {e}")
    
    def get_series_info(self, series_id: str) -> Dict[str, Any]:
        """Get information about a FRED series."""
        return self._make_request("series", {"series_id": series_id})
    
    def get_yield_curve_rates(self, observation_start: Optional[str] = None, 
                            observation_end: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Treasury yield curve rates.
        
        Common series IDs:
        - DGS10: 10-Year Treasury Constant Maturity Rate
        - DGS2: 2-Year Treasury Constant Maturity Rate  
        - DGS5: 5-Year Treasury Constant Maturity Rate
        - DGS30: 30-Year Treasury Constant Maturity Rate
        - DGS3MO: 3-Month Treasury Constant Maturity Rate
        - DGS1: 1-Year Treasury Constant Maturity Rate
        """
        
        # Default to last 30 days if no dates specified
        if not observation_end:
            # Use a recent historical date that exists in FRED
            observation_end = "2024-12-31"
        if not observation_start:
            start_date = datetime.strptime(observation_end, "%Y-%m-%d") - timedelta(days=30)
            observation_start = start_date.strftime("%Y-%m-%d")
        
        series_ids = ["DGS10", "DGS2", "DGS5", "DGS30", "DGS3MO", "DGS1"]
        yield_data = {}
        
        for series_id in series_ids:
            try:
                data = self._make_request("series/observations", {
                    "series_id": series_id,
                    "observation_start": observation_start,
                    "observation_end": observation_end,
                    "sort_order": "desc"
                })
                
                # Process observations
                observations = []
                for obs in data.get("observations", []):
                    if obs.get("value") != ".":
                        observations.append({
                            "date": obs["date"],
                            "rate": Decimal(obs["value"]),
                            "series_id": series_id
                        })
                
                yield_data[series_id] = {
                    "info": self.get_series_info(series_id),
                    "observations": observations
                }
                
            except Exception as e:
                print(f"Error fetching {series_id}: {e}")
                yield_data[series_id] = {"error": str(e)}
        
        return yield_data
    
    def calculate_yield_curve_metrics(self, yield_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate advanced yield curve metrics for financial modeling."""
        
        # Get latest rates for each maturity
        latest_rates = {}
        for series_id, data in yield_data.items():
            if "observations" in data and data["observations"]:
                latest_rates[series_id] = data["observations"][0]["rate"]
        
        if not latest_rates:
            return {"error": "No valid rate data available"}
        
        # Calculate common yield curve metrics
        metrics = {}
        
        # Basic spreads
        # 2s10s spread (2-year vs 10-year)
        if "DGS2" in latest_rates and "DGS10" in latest_rates:
            metrics["two_year_ten_year_spread"] = latest_rates["DGS10"] - latest_rates["DGS2"]
        
        # 5s30s spread (5-year vs 30-year) 
        if "DGS5" in latest_rates and "DGS30" in latest_rates:
            metrics["five_year_thirty_year_spread"] = latest_rates["DGS30"] - latest_rates["DGS5"]
        
        # 3m10s spread (3-month vs 10-year)
        if "DGS3MO" in latest_rates and "DGS10" in latest_rates:
            metrics["three_month_ten_year_spread"] = latest_rates["DGS10"] - latest_rates["DGS3MO"]
        
        # Advanced yield curve calculations
        if all(key in latest_rates for key in ["DGS3MO", "DGS2", "DGS5", "DGS10", "DGS30"]):
            # Calculate yield curve slope (bps per year)
            two_year_rate = float(latest_rates["DGS2"])
            ten_year_rate = float(latest_rates["DGS10"])
            thirty_year_rate = float(latest_rates["DGS30"])
            
            # Short-term slope (3m to 2y)
            metrics["short_term_slope"] = (two_year_rate - float(latest_rates["DGS3MO"])) / 1.75 * 100  # bps per year
            
            # Medium-term slope (2y to 10y)  
            metrics["medium_term_slope"] = (ten_year_rate - two_year_rate) / 8 * 100  # bps per year
            
            # Long-term slope (10y to 30y)
            metrics["long_term_slope"] = (thirty_year_rate - ten_year_rate) / 20 * 100  # bps per year
            
            # Overall curve steepness
            metrics["curve_steepness"] = (ten_year_rate - float(latest_rates["DGS3MO"])) / 9.75 * 100  # bps per year
            
            # Calculate forward rates (implied)
            # 1-year forward rate starting in 1 year
            metrics["one_year_forward_one_year"] = ((1 + ten_year_rate/100)**10 / (1 + two_year_rate/100)**2 - 1) * 100
            
            # 5-year forward rate starting in 5 years
            metrics["five_year_forward_five_year"] = ((1 + thirty_year_rate/100)**25 / (1 + ten_year_rate/100)**15 - 1) * 100
            
            # Yield curve positioning indicators
            avg_short_term = (float(latest_rates["DGS3MO"]) + two_year_rate) / 2
            avg_long_term = (ten_year_rate + thirty_year_rate) / 2
            
            if avg_short_term > avg_long_term:
                metrics["curve_position"] = "steep"
            elif avg_short_term < avg_long_term:
                metrics["curve_position"] = "flat"
            else:
                metrics["curve_position"] = "normal"
            
            # Risk indicators
            # Credit risk premium (corporate spread approximation)
            metrics["credit_risk_premium"] = ten_year_rate - float(latest_rates["DGS3MO"])
            
            # Term premium
            metrics["term_premium"] = thirty_year_rate - float(latest_rates["DGS3MO"])
            
            # Volatility indicator (spread range)
            short_end_spread = two_year_rate - float(latest_rates["DGS3MO"])
            long_end_spread = thirty_year_rate - ten_year_rate
            metrics["volatility_indicator"] = (short_end_spread + long_end_spread) / 2
        
        # Yield curve shape classification
        if "DGS2" in latest_rates and "DGS10" in latest_rates:
            spread = metrics["two_year_ten_year_spread"]
            if spread > 0.5:  # More than 50 bps
                metrics["curve_shape"] = "normal"
            elif spread < -0.5:  # More than -50 bps
                metrics["curve_shape"] = "inverted"
            else:
                metrics["curve_shape"] = "flat"
        
        # Economic indicators based on yield curve
        if all(key in metrics for key in ["short_term_slope", "medium_term_slope", "long_term_slope"]):
            # Recession signal (inverted yield curve)
            metrics["recession_signal"] = metrics["two_year_ten_year_spread"] < 0
            
            # Economic growth expectation
            if metrics["curve_steepness"] > 100:  # More than 1% per year
                metrics["growth_expectation"] = "strong"
            elif metrics["curve_steepness"] > 50:
                metrics["growth_expectation"] = "moderate"
            else:
                metrics["growth_expectation"] = "weak"
        
        return {
            "latest_rates": {k: float(v) for k, v in latest_rates.items()},
            "metrics": {k: float(v) for k, v in metrics.items() if isinstance(v, Decimal)},
            "timestamp": datetime.now().isoformat(),
            "data_quality": {
                "completeness": len([k for k in latest_rates.keys() if k in ["DGS3MO", "DGS2", "DGS5", "DGS10", "DGS30"]]) / 5,
                "freshness": "current"  # Could be enhanced with actual observation date
            }
        }


# Convenience function for getting yield curve data
def get_yield_curve_data(api_key: Optional[str] = None, days_back: int = 30) -> Dict[str, Any]:
    """Get complete yield curve data with calculations."""
    client = StLouisFedClient(api_key)
    
    # Get raw yield data
    yield_data = client.get_yield_curve_rates()
    
    # Calculate metrics
    metrics = client.calculate_yield_curve_metrics(yield_data)
    
    return {
        "yield_data": yield_data,
        "calculated_metrics": metrics
    }
