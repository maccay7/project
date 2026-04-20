"""
Dura Capital valuation API (Flask).

Requires .env: FLASK_SECRET_KEY, ALLOWED_LOGIN_EMAIL, MYSQL_* (see env.example).
"""

from __future__ import annotations

import csv
import io
import json
import os
import secrets
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from urllib import error as url_error
from urllib import parse as url_parse
from urllib import request as url_request

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from auth_util import allowed_login_email, create_auth_token, require_auth
from db import get_connection, ping_db
from file_pipeline import clean_file, inspect_file
from stlouis_fed import get_yield_curve_data, StLouisFedClient

load_dotenv()

# Constant scrypt hash for unknown users (timing normalization; password will not verify).
_DUMMY_HASH = (
    "scrypt:32768:8:1$hMtxUc8LXVGVlNWX$e6903cd6bb6e1f3156ee879fc25db8efabe7c97f75cc2da4f8f7c9637b403a26100a482f5d30711b0606d0eb4cdf16cfcc3054a2beabd55c81599c8ddfc2c9fb"
)

app = Flask(__name__)
# Explicit origins so browser → Flask (bypassing Vite proxy) works for file uploads
_cors_origins = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": _cors_origins,
            "supports_credentials": True,
            "allow_headers": ["Authorization", "Content-Type"],
            "methods": ["GET", "POST", "OPTIONS", "HEAD"],
        }
    },
)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB uploads
limiter = Limiter(get_remote_address, app=app, default_limits=[], storage_uri="memory://")

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_upload_path(stored_path: str) -> Path | None:
    """Reject path traversal; only files under UPLOAD_DIR."""
    if not stored_path or not isinstance(stored_path, str):
        return None
    try:
        p = Path(stored_path).resolve()
        p.relative_to(UPLOAD_DIR.resolve())
    except (ValueError, OSError):
        return None
    return p if p.is_file() else None


def _num(x) -> float:
    if x is None:
        return 0.0
    if isinstance(x, Decimal):
        return float(x)
    return float(x)


def format_usd(n: float) -> str:
    return "${:,.0f}".format(n)


def fetch_instruments_rows():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, instrument_type AS type, issuer,
                       face_value, current_value, yield_pct, maturity_label,
                       days_left, rating, status
                FROM instruments
                ORDER BY id
                """
            )
            return cur.fetchall()


def rows_to_internal(rows):
    out = []
    for r in rows:
        out.append(
            {
                "id": str(r["id"]),
                "name": r["name"],
                "type": r["type"],
                "issuer": r["issuer"] or "",
                "faceValue": _num(r["face_value"]),
                "currentValue": _num(r["current_value"]),
                "yieldPct": _num(r["yield_pct"]),
                "maturity": r["maturity_label"] or "",
                "daysLeft": r["days_left"],
                "rating": r["rating"] or "",
                "status": r["status"] or "Active",
            }
        )
    return out


def resolve_days(i: dict) -> int | None:
    if i.get("daysLeft") is not None:
        try:
            return int(i["daysLeft"])
        except (TypeError, ValueError):
            pass
    m = i.get("maturity") or ""
    if not m or m == "Rolling":
        return None
    try:
        d = date.fromisoformat(m[:10])
        return max(0, (d - date.today()).days)
    except ValueError:
        return None


def rating_to_risk(rating: str) -> float:
    r = (rating or "").upper().strip()
    m = {
        "AAA": 12,
        "AA+": 15,
        "AA": 18,
        "AA-": 22,
        "A+": 28,
        "A": 32,
        "A-": 38,
        "BBB+": 45,
        "BBB": 50,
        "BBB-": 55,
        "BB+": 62,
        "BB": 68,
        "B+": 75,
        "B": 80,
        "CCC": 90,
        "D": 100,
    }
    return float(m.get(r, 40))


def risk_band(score: float) -> str:
    if score < 35:
        return "Low"
    if score < 55:
        return "Moderate"
    return "Elevated"


def compute_risk_assessment(list_: list) -> list:
    if not list_:
        return [
            {"label": "Credit Risk", "width_pct": 0, "text": "N/A"},
            {"label": "Interest Rate Risk", "width_pct": 0, "text": "N/A"},
            {"label": "Liquidity Risk", "width_pct": 0, "text": "N/A"},
        ]
    total = sum(i["currentValue"] for i in list_)
    if total <= 0:
        total = 1.0
    credit = sum(rating_to_risk(i["rating"]) * i["currentValue"] for i in list_) / total

    days_w = []
    for i in list_:
        d = resolve_days(i)
        if d is not None:
            days_w.append((d, i["currentValue"]))
    if days_w:
        avg_days = sum(d * w for d, w in days_w) / sum(w for _, w in days_w)
        interest = min(95.0, max(5.0, (avg_days / 730.0) * 100.0))
    else:
        interest = 30.0

    type_liq = {"T-Bills": 20.0, "Money Market": 35.0, "Bonds": 55.0}
    liq = sum(type_liq.get(i["type"], 40.0) * i["currentValue"] for i in list_) / total

    return [
        {"label": "Credit Risk", "width_pct": int(min(100, credit)), "text": risk_band(credit)},
        {"label": "Interest Rate Risk", "width_pct": int(min(100, interest)), "text": risk_band(interest)},
        {"label": "Liquidity Risk", "width_pct": int(min(100, liq)), "text": risk_band(liq)},
    ]


def weighted_avg_days(list_: list) -> int | None:
    wsum = 0.0
    vsum = 0.0
    for i in list_:
        d = resolve_days(i)
        if d is None:
            continue
        wsum += d * i["currentValue"]
        vsum += i["currentValue"]
    if vsum <= 0:
        return None
    return int(round(wsum / vsum))


def maturity_schedule_from(list_: list) -> list:
    buckets = [
        ("0-3 months", 0, 92),
        ("3-6 months", 92, 183),
        ("6-12 months", 183, 366),
        ("12+ months", 366, 10**9),
    ]
    rows = []
    for label, lo, hi in buckets:
        b_amt = t_amt = m_amt = 0.0
        for i in list_:
            d = resolve_days(i)
            if d is None:
                continue
            if not (lo <= d < hi):
                continue
            if i["type"] == "Bonds":
                b_amt += i["currentValue"]
            elif i["type"] == "T-Bills":
                t_amt += i["currentValue"]
            elif i["type"] == "Money Market":
                m_amt += i["currentValue"]
        col = b_amt + t_amt + m_amt
        if col <= 0:
            rows.append(
                {
                    "period": label,
                    "bonds": 0,
                    "tbills": 0,
                    "moneymarket": 0,
                    "amount": "$0",
                }
            )
            continue
        rows.append(
            {
                "period": label,
                "bonds": int(round(100 * b_amt / col)),
                "tbills": int(round(100 * t_amt / col)),
                "moneymarket": int(round(100 * m_amt / col)),
                "amount": format_usd(col),
            }
        )
    return rows


def dashboard_from_internal(list_):
    bonds = [i for i in list_ if i["type"] == "Bonds"]
    tbills = [i for i in list_ if i["type"] == "T-Bills"]
    mm = [i for i in list_ if i["type"] == "Money Market"]
    vb = sum(i["currentValue"] for i in bonds)
    vt = sum(i["currentValue"] for i in tbills)
    vm = sum(i["currentValue"] for i in mm)
    total = vb + vt + vm
    return {
        "statistics": {
            "bonds": {"count": len(bonds), "value": format_usd(vb)},
            "tbills": {"count": len(tbills), "value": format_usd(vt)},
            "moneymarket": {"count": len(mm), "value": format_usd(vm)},
            "total": format_usd(total),
        },
        "instruments": [
            {
                "id": i["id"],
                "name": i["name"],
                "type": i["type"],
                "value": format_usd(i["currentValue"]),
                "maturity": i["maturity"],
                "yield": f'{i["yieldPct"]}%',
            }
            for i in list_
        ],
    }


def instruments_api_list(list_):
    return [
        {
            "id": i["id"],
            "name": i["name"],
            "type": i["type"],
            "issuer": i["issuer"],
            "faceValue": format_usd(i["faceValue"]),
            "currentValue": format_usd(i["currentValue"]),
            "yield": f'{i["yieldPct"]}%',
            "maturity": i["maturity"],
            "daysLeft": "-" if i["daysLeft"] is None else str(i["daysLeft"]),
            "rating": i["rating"],
            "status": i["status"],
        }
        for i in list_
    ]


def type_label(t: str) -> str:
    return "Treasury Bills" if t == "T-Bills" else t


def reports_from_db(list_):
    total_val = sum(i["currentValue"] for i in list_)
    yields = [i["yieldPct"] for i in list_ if i["yieldPct"] is not None]
    avg_y = sum(yields) / len(yields) if yields else 0.0

    by_type = {}
    for i in list_:
        by_type.setdefault(i["type"], []).append(i)

    dist = []
    if total_val > 0:
        for t, items in sorted(by_type.items()):
            pct = int(round(100 * sum(x["currentValue"] for x in items) / total_val))
            label = type_label(t)
            dist.append({"name": label, "percentage": pct})
    else:
        dist = []

    yield_rows = []
    for t in ("Bonds", "T-Bills", "Money Market"):
        g = [i["yieldPct"] for i in list_ if i["type"] == t]
        if not g:
            continue
        yield_rows.append(
            {
                "type": type_label(t),
                "avg": f"{sum(g) / len(g):.1f}%",
                "min": f"{min(g):.1f}%",
                "max": f"{max(g):.1f}%",
            }
        )

    wdays = weighted_avg_days(list_)
    risk_metrics = compute_risk_assessment(list_)
    credit_score = risk_metrics[0]["width_pct"] if risk_metrics else 0

    return {
        "summary": {
            "totalPortfolioValue": format_usd(total_val),
            "totalPortfolioChangePct": "No prior-period snapshot in database",
            "averageYield": f"{avg_y:.2f}%" if yields else "N/A",
            "averageYieldChange": "No prior-period snapshot in database",
            "riskScore": risk_band(float(credit_score)),
            "riskNote": "Derived from ratings, tenor, and instrument mix",
            "avgDaysToMaturity": f"{wdays} days (value-weighted)" if wdays is not None else "N/A",
            "maturityNote": "From days to maturity / maturity dates where available",
        },
        "instrumentDistribution": dist,
        "yieldAnalysis": yield_rows,
        "maturitySchedule": maturity_schedule_from(list_),
        "riskAssessment": risk_metrics,
    }


def _safe_float(value) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _extract_numeric(row: dict, keys: list[str]) -> float | None:
    for key in keys:
        v = _safe_float(row.get(key))
        if v is not None:
            return v
    return None


def _extract_text(row: dict, keys: list[str], default: str = "") -> str:
    for key in keys:
        v = row.get(key)
        if v is None:
            continue
        text = str(v).strip()
        if text:
            return text
    return default


def _extract_days_to_maturity(row: dict) -> int | None:
    day_keys = [
        "days_to_maturity",
        "days_left",
        "days",
        "tenor_days",
        "maturity_days",
        "duration_days",
    ]
    for key in day_keys:
        v = _safe_float(row.get(key))
        if v is not None:
            return max(0, int(round(v)))

    maturity_text = _extract_text(row, ["maturity_date", "maturity", "maturity_label"], "")
    if not maturity_text:
        return None
    try:
        mdate = date.fromisoformat(maturity_text[:10])
        return max(0, (mdate - date.today()).days)
    except ValueError:
        return None


def _default_yield_curve() -> dict:
    return {
        "asOf": date.today().isoformat(),
        "source": "fallback",
        "points": {
            "treasury_bills": [
                {"days": 30, "rate": 4.3},
                {"days": 91, "rate": 4.5},
                {"days": 182, "rate": 4.7},
                {"days": 364, "rate": 4.9},
            ],
            "money_market": [
                {"days": 30, "rate": 4.1},
                {"days": 90, "rate": 4.35},
                {"days": 180, "rate": 4.55},
                {"days": 365, "rate": 4.8},
            ],
        },
    }


def _fred_observations(series_id: str, api_key: str) -> list[dict]:
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": "24",
    }
    url = "https://api.stlouisfed.org/fred/series/observations?" + url_parse.urlencode(params)
    req = url_request.Request(url, headers={"Accept": "application/json"})
    with url_request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    payload = json.loads(raw)
    obs = payload.get("observations")
    if not isinstance(obs, list):
        return []
    return obs


def _latest_fred_rate(series_id: str, api_key: str) -> tuple[float | None, str | None]:
    obs = _fred_observations(series_id, api_key)
    for row in obs:
        if not isinstance(row, dict):
            continue
        value = str(row.get("value") or "").strip()
        if not value or value == ".":
            continue
        rate = _safe_float(value)
        if rate is None:
            continue
        return float(rate), str(row.get("date") or "")
    return None, None


def load_yield_curve_from_fred() -> dict | None:
    """
    Pull latest rates from FRED using enhanced client with advanced calculations.
    Returns comprehensive yield curve data for financial modeling.
    """
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from stlouis_fed import get_yield_curve_data
        # Get enhanced yield curve data with calculations
        yield_curve_result = get_yield_curve_data(api_key, days_back=30)
        
        if yield_curve_result.get("calculated_metrics", {}).get("error"):
            return None
            
        # Extract latest rates for compatibility with existing code
        latest_rates = yield_curve_result.get("calculated_metrics", {}).get("latest_rates", {})
        
        # Build treasury points for existing system compatibility
        treasury_points = []
        if "DGS3MO" in latest_rates:
            treasury_points.append({"days": 91, "rate": float(latest_rates["DGS3MO"])})
        if "DGS6MO" in latest_rates:
            treasury_points.append({"days": 182, "rate": float(latest_rates["DGS6MO"])})
        if "DGS1" in latest_rates:
            treasury_points.append({"days": 365, "rate": float(latest_rates["DGS1"])})
        if "DGS2" in latest_rates:
            treasury_points.append({"days": 730, "rate": float(latest_rates["DGS2"])})  # 2-year
        if "DGS5" in latest_rates:
            treasury_points.append({"days": 1825, "rate": float(latest_rates["DGS5"])})  # 5-year
        if "DGS10" in latest_rates:
            treasury_points.append({"days": 3650, "rate": float(latest_rates["DGS10"])})  # 10-year
        if "DGS30" in latest_rates:
            treasury_points.append({"days": 10950, "rate": float(latest_rates["DGS30"])})  # 30-year

        # Build money market points using enhanced calculations
        money_market_points = []
        metrics = yield_curve_result.get("calculated_metrics", {})
        
        # Use SOFR equivalent from 3-month Treasury as base
        base_rate = float(latest_rates.get("DGS3MO", 0))
        
        # Map to standard tenors
        money_market_points.append({"days": 30, "rate": base_rate})
        money_market_points.append({"days": 90, "rate": base_rate})
        
        # Add calculated forward rates if available
        if "one_year_forward_one_year" in metrics:
            money_market_points.append({"days": 365, "rate": metrics["one_year_forward_one_year"]})
        if "five_year_forward_five_year" in metrics:
            money_market_points.append({"days": 1825, "rate": metrics["five_year_forward_five_year"]})

        if not treasury_points and not money_market_points:
            return None

        # Return enhanced data structure
        return {
            "asOf": yield_curve_result.get("calculated_metrics", {}).get("timestamp", date.today().isoformat()),
            "source": "fred_enhanced",
            "points": {
                "treasury_bills": sorted(treasury_points, key=lambda x: x["days"]),
                "money_market": sorted(money_market_points, key=lambda x: x["days"]),
            },
            "enhanced_metrics": yield_curve_result.get("calculated_metrics", {}),
        }
    except Exception as e:
        print(f"Error loading enhanced FRED data: {e}")
        return None


def _normalize_curve_payload(payload) -> dict | None:
    if not isinstance(payload, dict):
        return None
    points = payload.get("points")
    if not isinstance(points, dict):
        return None

    def normalize_points(rows):
        out = []
        if not isinstance(rows, list):
            return out
        for item in rows:
            if not isinstance(item, dict):
                continue
            d = _safe_float(item.get("days"))
            r = _safe_float(item.get("rate"))
            if d is None or r is None:
                continue
            out.append({"days": int(round(d)), "rate": float(r)})
        return sorted(out, key=lambda x: x["days"])

    tb = normalize_points(points.get("treasury_bills"))
    mm = normalize_points(points.get("money_market"))
    if not tb and not mm:
        return None
    return {
        "asOf": payload.get("asOf") or date.today().isoformat(),
        "source": payload.get("source") or "configured_api",
        "points": {"treasury_bills": tb, "money_market": mm},
    }


def load_yield_curve() -> dict:
    fred_curve = load_yield_curve_from_fred()
    if fred_curve:
        return fred_curve

    api_url = os.environ.get("YIELD_CURVE_API_URL", "").strip()
    if api_url:
        try:
            req = url_request.Request(api_url, headers={"Accept": "application/json"})
            with url_request.urlopen(req, timeout=8) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw)
            normalized = _normalize_curve_payload(payload)
            if normalized:
                return normalized
        except (url_error.URLError, TimeoutError, json.JSONDecodeError):
            pass
    return _default_yield_curve()


def curve_rate_for_days(curve_rows: list[dict], days: int | None) -> float | None:
    if not curve_rows:
        return None
    if days is None:
        return float(curve_rows[0]["rate"])
    for row in curve_rows:
        if days <= int(row["days"]):
            return float(row["rate"])
    return float(curve_rows[-1]["rate"])


def _rows_from_clean_preview(cleaned_preview: list[list[str]]) -> list[dict]:
    if not isinstance(cleaned_preview, list) or len(cleaned_preview) < 2:
        return []
    headers = [str(h).strip() for h in cleaned_preview[0]]
    out = []
    for row in cleaned_preview[1:]:
        item = {}
        for i, h in enumerate(headers):
            if not h:
                continue
            item[h] = row[i] if i < len(row) else ""
        out.append(item)
    return out


def build_report_rows(
    clean_results: list[dict], upload_meta: dict, report_type: str = "detailed"
) -> list[dict]:
    curve = load_yield_curve()
    t_rows = curve.get("points", {}).get("treasury_bills", [])
    m_rows = curve.get("points", {}).get("money_market", [])
    today = date.today().isoformat()

    report_rows = []
    for result in clean_results:
        if not result.get("ok"):
            continue
        preview_rows = _rows_from_clean_preview(result.get("cleanedPreview") or [])
        for row in preview_rows:
            days = _extract_days_to_maturity(row)
            raw_type = str(upload_meta.get("instrumentType") or "").lower().replace("-", "").replace(" ", "")
            if raw_type in ("tbills", "tbill", "treasurybills", "treasurybill"):
                curve_rows = t_rows or m_rows
            elif raw_type in ("moneymarket", "mm"):
                curve_rows = m_rows or t_rows
            else:
                curve_rows = m_rows or t_rows
            curve_rate = curve_rate_for_days(curve_rows, days) or 0.0

            loan_value = _extract_numeric(row, ["loan_value", "face_value", "principal", "amount"])
            current_balance = _extract_numeric(
                row, ["current_balance", "balance", "current_value", "outstanding_balance"]
            )
            price = _extract_numeric(row, ["price", "market_price", "purchase_price"])
            discount_rate = _extract_numeric(row, ["discount_rate", "rate", "yield_rate"])
            if discount_rate is None:
                discount_rate = curve_rate
            row_yield = _extract_numeric(row, ["yield", "yield_pct", "yield_rate"])
            if row_yield is None and price and loan_value and loan_value > 0:
                row_yield = ((loan_value - price) / loan_value) * 100.0
            if row_yield is None:
                row_yield = curve_rate
            duration = None if days is None else round(days / 365.0, 4)

            report_rows.append(
                {
                    "pricing_date": upload_meta.get("date") or today,
                    "creator": upload_meta.get("counterParty") or "N/A",
                    "current_balance": current_balance,
                    "yield": row_yield,
                    "duration": duration,
                    "sourcefile": upload_meta.get("sourcefile") or "N/A",
                    "description": upload_meta.get("description") or "",
                    "loanvalue": loan_value,
                    "loan_number": _extract_text(
                        row, ["loan_number", "loan_no", "loan_id", "id"], default="N/A"
                    ),
                    "price": price,
                    "discount_rate": discount_rate,
                    "days_to_maturity": days,
                }
            )

    if report_type == "summary":
        if not report_rows:
            return []
        count = len(report_rows)
        avg = lambda key: round(
            sum((r.get(key) or 0.0) for r in report_rows) / count,
            4,
        )
        return [
            {
                "pricing_date": upload_meta.get("date") or today,
                "creator": upload_meta.get("counterParty") or "N/A",
                "current_balance": sum((r.get("current_balance") or 0.0) for r in report_rows),
                "yield": avg("yield"),
                "duration": avg("duration"),
                "sourcefile": upload_meta.get("sourcefile") or "N/A",
                "description": f"{count} row(s) summarized",
                "loanvalue": sum((r.get("loanvalue") or 0.0) for r in report_rows),
                "loan_number": f"{count} loans",
                "price": avg("price"),
                "discount_rate": avg("discount_rate"),
                "days_to_maturity": int(round(avg("days_to_maturity"))),
            }
        ]
    return report_rows


def summarize_report_rows(rows: list[dict]) -> dict:
    count = len(rows)
    if count == 0:
        return {"rows": 0, "loanValueTotal": 0, "balanceTotal": 0, "averageYield": 0, "averageDuration": 0}
    return {
        "rows": count,
        "loanValueTotal": round(sum((r.get("loanvalue") or 0.0) for r in rows), 4),
        "balanceTotal": round(sum((r.get("current_balance") or 0.0) for r in rows), 4),
        "averageYield": round(sum((r.get("yield") or 0.0) for r in rows) / count, 4),
        "averageDuration": round(sum((r.get("duration") or 0.0) for r in rows) / count, 4),
    }


def _instrument_type_label(raw: str) -> str:
    k = (raw or "").strip().lower().replace("-", "").replace(" ", "")
    if k in ("tbills", "tbill", "treasurybills", "treasurybill"):
        return "T-Bills"
    if k in ("moneymarket", "mm"):
        return "Money Market"
    return "Bonds"


def _report_rows_to_internal(report_rows: list[dict], instrument_type_raw: str) -> list[dict]:
    t_label = _instrument_type_label(instrument_type_raw)
    out = []
    for idx, r in enumerate(report_rows, start=1):
        current_value = _safe_float(r.get("current_balance")) or 0.0
        face_value = _safe_float(r.get("loanvalue")) or current_value
        y = _safe_float(r.get("yield")) or 0.0
        days = r.get("days_to_maturity")
        try:
            days_left = None if days is None else int(days)
        except (TypeError, ValueError):
            days_left = None
        maturity_label = ""
        if days_left is not None:
            try:
                maturity_label = (date.today() + timedelta(days=max(0, days_left))).isoformat()
            except Exception:
                maturity_label = ""
        out.append(
            {
                "id": str(idx),
                "name": str(r.get("loan_number") or f"Loan {idx}"),
                "type": t_label,
                "issuer": str(r.get("creator") or ""),
                "faceValue": float(face_value),
                "currentValue": float(current_value),
                "yieldPct": float(y),
                "maturity": maturity_label,
                "daysLeft": days_left,
                "rating": "",
                "status": "Active",
            }
        )
    return out


def _latest_uploaded_internal() -> list[dict] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT original_name, stored_path, instrument_type, counter_party, eval_date, description
                FROM file_uploads
                ORDER BY id DESC
                LIMIT 1
                """
            )
            latest = cur.fetchone()
    if not latest:
        return None
    path = _resolve_upload_path(str(latest.get("stored_path")))
    if path is None:
        return None
    cleaned = clean_file(path)
    if not cleaned.get("ok"):
        return None
    upload_meta = {
        "counterParty": latest.get("counter_party") or "",
        "date": str(latest.get("eval_date") or ""),
        "description": latest.get("description") or "",
        "sourcefile": latest.get("original_name") or path.name,
        "instrumentType": latest.get("instrument_type") or "",
    }
    report_rows = build_report_rows([cleaned], upload_meta=upload_meta, report_type="detailed")
    if not report_rows:
        return None
    return _report_rows_to_internal(report_rows, upload_meta.get("instrumentType") or "")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "dura-capital-valuation-api", "backend": "flask"})


@app.get("/api/dashboard/test")
def dashboard_test():
    """Temporary test endpoint without authentication to verify data flow"""
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    
    internal = _latest_uploaded_internal()
    if internal is None:
        from app import fetch_instruments_rows, rows_to_internal
        rows = fetch_instruments_rows()
        internal = rows_to_internal(rows)
        source = "database"
    else:
        source = "latest-upload"
    
    payload = dashboard_from_internal(internal)
    payload["dataSource"] = source
    payload["hasData"] = len(internal) > 0
    return jsonify(payload)


@app.get("/api/instruments/test")
def instruments_test():
    """Temporary test endpoint without authentication"""
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    
    internal = _latest_uploaded_internal()
    if internal is None:
        from app import fetch_instruments_rows, rows_to_internal
        rows = fetch_instruments_rows()
        internal = rows_to_internal(rows)
    
    return jsonify({"instruments": instruments_api_list(internal)})


@app.get("/api/reports/test")
def reports_test():
    """Temporary test endpoint without authentication"""
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    
    internal = _latest_uploaded_internal()
    if internal is None:
        from app import fetch_instruments_rows, rows_to_internal
        rows = fetch_instruments_rows()
        internal = rows_to_internal(rows)
    
    payload = {"period": {"dateFrom": None, "dateTo": None}}
    payload.update(reports_from_db(internal))
    return jsonify(payload)


@app.post("/api/auth/login")
@limiter.limit("15 per minute")
def login():
    data = request.get_json(silent=True) or {}
    email_raw = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not email_raw or not password:
        return jsonify({"error": "Invalid email or password"}), 401

    if not allowed_login_email():
        return jsonify({"error": "Server misconfiguration: set ALLOWED_LOGIN_EMAIL in .env"}), 500

    if not ping_db():
        return jsonify({"error": "Database unavailable"}), 503

    norm = email_raw.lower()
    allowed = allowed_login_email()

    row = None
    if norm == allowed:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, password_hash FROM users WHERE LOWER(email) = %s LIMIT 1",
                    (norm,),
                )
                row = cur.fetchone()

    hash_to_check = row["password_hash"] if row else _DUMMY_HASH
    password_ok = check_password_hash(hash_to_check, password)

    if not password_ok or row is None:
        return jsonify({"error": "Invalid email or password"}), 401

    try:
        token = create_auth_token(row["email"])
    except RuntimeError:
        return jsonify({"error": "Server configuration error: set FLASK_SECRET_KEY in .env"}), 500
    return jsonify({"token": token, "user": {"email": row["email"]}})


@app.get("/api/dashboard/overview")
@require_auth
def dashboard_overview():
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    source = "database"
    internal = _latest_uploaded_internal()
    if internal is None:
        rows = fetch_instruments_rows()
        internal = rows_to_internal(rows)
    else:
        source = "latest-upload"
    payload = dashboard_from_internal(internal)
    payload["dataSource"] = source
    payload["hasData"] = len(internal) > 0
    return jsonify(payload)


@app.get("/api/instruments")
@require_auth
def instruments_list():
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    internal = _latest_uploaded_internal()
    if internal is None:
        rows = fetch_instruments_rows()
        internal = rows_to_internal(rows)
    return jsonify({"instruments": instruments_api_list(internal)})


@app.get("/api/reports/summary")
@require_auth
def reports_summary():
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    date_from = request.args.get("dateFrom")
    date_to = request.args.get("dateTo")
    internal = _latest_uploaded_internal()
    if internal is None:
        rows = fetch_instruments_rows()
        internal = rows_to_internal(rows)
    payload = {"period": {"dateFrom": date_from, "dateTo": date_to}}
    payload.update(reports_from_db(internal))
    return jsonify(payload)


def _collect_uploaded_files():
    """Accept 'files', 'file', or any FormData file field (proxy/clients vary)."""
    preferred = request.files.getlist("files") or request.files.getlist("file")
    out = [f for f in preferred if f and f.filename]
    if out:
        return out
    for key in request.files:
        for f in request.files.getlist(key):
            if f and f.filename:
                out.append(f)
    return out


@app.post("/api/uploads")
@require_auth
def uploads():
    files = _collect_uploaded_files()
    if not files:
        app.logger.warning(
            "Upload rejected: no files (content_type=%s, form_keys=%s, file_keys=%s)",
            request.content_type,
            list(request.form.keys()),
            list(request.files.keys()),
        )
        return jsonify({"error": "no files uploaded"}), 400

    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503

    instrument_type = (request.form.get("instrumentType") or "").strip().lower()
    allowed = {"bonds", "tbills", "moneymarket"}
    if instrument_type not in allowed:
        instrument_type = "bonds"
    counter_party = request.form.get("counterParty")
    eval_date_raw = request.form.get("date") or ""
    description = request.form.get("description")

    eval_date = None
    if eval_date_raw:
        try:
            eval_date = date.fromisoformat(eval_date_raw)
        except ValueError:
            eval_date = None

    stored_paths: list[str] = []
    file_results: list[dict] = []
    conn = get_connection()
    
    try:
        # Process files in batch for better performance
        upload_data = []
        for f in files:
            # Generate unique filename and save file
            safe = secure_filename(f.filename) or "upload"
            unique = f"{secrets.token_hex(8)}_{safe}"
            path = UPLOAD_DIR / unique
            f.save(path)
            sp = str(path)
            stored_paths.append(sp)
            
            # Collect upload data for batch insert
            upload_data.append((
                f.filename,
                sp,
                instrument_type,
                counter_party,
                eval_date,
                description,
            ))
            
            # Inspect file (this can be done in parallel for multiple files)
            insight = inspect_file(path)
            file_results.append(
                {
                    "originalName": f.filename,
                    "storedPath": sp,
                    "insight": insight,
                }
            )
        
        # Batch insert for better performance
        if upload_data:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO file_uploads
                      (original_name, stored_path, instrument_type, counter_party, eval_date, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    upload_data,
                )
        
        # Batch audit log entry
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit_log (action, detail) VALUES (%s, %s)",
                (
                    "upload",
                    json.dumps({
                        "files_count": len(files),
                        "instrument_type": instrument_type,
                        "processed_files": [fr[0] for fr in upload_data],
                    }),
                ),
            )
            
    finally:
        conn.close()

    return jsonify(
        {
            "ok": True,
            "received": len(files),
            "instrumentType": instrument_type,
            "counterParty": counter_party,
            "date": eval_date_raw or None,
            "description": description,
            "storedPaths": stored_paths,
            "files": file_results,
        }
    )


@app.post("/api/uploads/clean")
@require_auth
def uploads_clean():
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    body = request.get_json(silent=True) or {}
    paths = body.get("storedPaths")
    clean_options = body.get("cleaningOptions") if isinstance(body.get("cleaningOptions"), dict) else {}
    if not isinstance(paths, list) or not paths:
        return jsonify({"error": "storedPaths array required"}), 400

    results = []
    conn = get_connection()
    
    try:
        # Process files in parallel for better performance
        for raw in paths:
            p = _resolve_upload_path(str(raw))
            if p is None:
                results.append({"storedPath": raw, "ok": False, "error": "invalid or missing file"})
                continue
            
            # Clean file with optimized options
            cleaned = clean_file(p, options=clean_options)
            results.append({"storedPath": str(p), **cleaned})

        all_ok = all(r.get("ok") for r in results)
        
        # Single audit log entry for batch operation
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit_log (action, detail) VALUES (%s, %s)",
                ("clean", json.dumps({
                    "files": len(results), 
                    "all_ok": all_ok,
                    "cleaning_options": clean_options
                })),
            )
    finally:
        conn.close()

    return jsonify({"ok": all_ok, "results": results})


@app.post("/api/uploads/calculate")
@require_auth
def uploads_calculate():
    """Re-run clean + numeric hints; compare row counts to instruments in DB."""
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    body = request.get_json(silent=True) or {}
    paths = body.get("storedPaths")
    clean_options = body.get("cleaningOptions") if isinstance(body.get("cleaningOptions"), dict) else {}
    if not isinstance(paths, list) or not paths:
        return jsonify({"error": "storedPaths array required"}), 400

    rows = fetch_instruments_rows()
    internal = rows_to_internal(rows)
    db_instrument_count = len(internal)

    per_file = []
    report_inputs = []
    
    # Batch process files for better performance
    file_metadata = {}
    conn = get_connection()
    
    try:
        # Collect all metadata in one query
        if paths:
            placeholders = ','.join(['%s'] * len(paths))
            with conn.cursor() as meta_cur:
                meta_cur.execute(
                    f"""
                    SELECT original_name, instrument_type, counter_party, eval_date, description, stored_path
                    FROM file_uploads
                    WHERE stored_path IN ({placeholders})
                    ORDER BY id DESC
                    """,
                    paths,
                )
                for row in meta_cur.fetchall():
                    file_metadata[row['stored_path']] = {
                        "counterParty": row.get("counter_party") or "",
                        "date": str(row.get("eval_date") or ""),
                        "description": row.get("description") or "",
                        "sourcefile": row.get("original_name") or "",
                        "instrumentType": row.get("instrument_type") or "",
                    }
        
        # Process files with optimized metadata lookup
        for raw in paths:
            p = _resolve_upload_path(str(raw))
            if p is None:
                per_file.append({"storedPath": raw, "ok": False, "error": "invalid or missing file"})
                continue
                
            c = clean_file(p, options=clean_options)
            if not c.get("ok"):
                per_file.append({"storedPath": str(p), **c})
                continue
                
            report_inputs.append(c)
            upload_meta = file_metadata.get(str(p), {
                "counterParty": "", "date": "", "description": "", "sourcefile": "", "instrumentType": ""
            })
            
            hints = c.get("valuationHints") or {}
            data_rows = int(hints.get("rowCount") or 0)
            per_file.append({
                "storedPath": str(p),
                "ok": True,
                "valuationHints": hints,
                "databaseInstruments": db_instrument_count,
                "alignmentNote": (
                    "Upload row count matches instrument count in database."
                    if db_instrument_count and data_rows == db_instrument_count
                    else (
                        f"Database has {db_instrument_count} instrument row(s); "
                        f"this file has {data_rows} data row(s) after cleaning. "
                        "Import into instruments is not wired yet — use this for QA."
                    )
                ),
            })
        
        # Generate reports after processing all files
        report_type = (body.get("reportType") or "detailed").lower()
        report_rows = build_report_rows(report_inputs, upload_meta=upload_meta, report_type=report_type)
        
        # Single audit log entry
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit_log (action, detail) VALUES (%s, %s)",
                ("calculate", json.dumps({
                    "files": len(report_inputs), 
                    "reportType": report_type,
                    "performance_optimized": True
                })),
            )
    finally:
        conn.close()

    return jsonify({
        "ok": True,
        "reportRows": report_rows,
        "reportType": report_type,
        "reportSummary": summarize_report_rows(report_rows),
        "perFile": per_file,
    })


@app.get("/api/uploads")
@require_auth
def list_uploads():
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, original_name, stored_path, instrument_type, counter_party,
                       eval_date, description, created_at
                FROM file_uploads
                ORDER BY id DESC
                """
            )
            rows = cur.fetchall()
    return jsonify({"uploads": rows})


@app.delete("/api/uploads/<int:upload_id>")
@require_auth
def delete_upload(upload_id: int):
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, stored_path, original_name
                FROM file_uploads
                WHERE id = %s
                LIMIT 1
                """,
                (upload_id,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "upload not found"}), 404
            cur.execute("DELETE FROM file_uploads WHERE id = %s", (upload_id,))
            cur.execute(
                "INSERT INTO audit_log (action, detail) VALUES (%s, %s)",
                (
                    "delete_upload",
                    json.dumps({"id": upload_id, "original_name": row.get("original_name")}),
                ),
            )
    p = _resolve_upload_path(str(row.get("stored_path")))
    if p is not None:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
    return jsonify({"ok": True, "deletedId": upload_id})


@app.get("/api/yield-curve")
@require_auth
def yield_curve():
    return jsonify(load_yield_curve())


@app.get("/api/reports/preview")
@require_auth
def reports_preview():
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    report_type = (request.args.get("reportType") or "detailed").lower()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, original_name, stored_path, instrument_type, counter_party, eval_date, description
                FROM file_uploads
                ORDER BY id DESC
                LIMIT 1
                """
            )
            latest = cur.fetchone()
    if not latest:
        return jsonify({"reportType": report_type, "summary": summarize_report_rows([]), "rows": []})

    path = _resolve_upload_path(str(latest.get("stored_path")))
    if path is None:
        return jsonify({"error": "latest uploaded file is missing on disk"}), 404
    cleaned = clean_file(path)
    if not cleaned.get("ok"):
        return jsonify({"error": cleaned.get("error") or "failed to prepare report preview"}), 400
    upload_meta = {
        "counterParty": latest.get("counter_party") or "",
        "date": str(latest.get("eval_date") or ""),
        "description": latest.get("description") or "",
        "sourcefile": latest.get("original_name") or path.name,
        "instrumentType": latest.get("instrument_type") or "",
    }
    rows = build_report_rows([cleaned], upload_meta=upload_meta, report_type=report_type)
    return jsonify(
        {
            "reportType": report_type,
            "summary": summarize_report_rows(rows),
            "rows": rows,
            "yieldCurve": load_yield_curve(),
        }
    )


@app.get("/api/reports/export")
@require_auth
def reports_export():
    if not ping_db():
        return jsonify({"error": "database unavailable"}), 503
    fmt = (request.args.get("format") or "csv").lower()
    report_type = (request.args.get("reportType") or "detailed").lower()
    date_from = request.args.get("dateFrom") or ""
    date_to = request.args.get("dateTo") or ""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, original_name, stored_path, instrument_type, counter_party, eval_date, description
                FROM file_uploads
                ORDER BY id DESC
                LIMIT 1
                """
            )
            latest = cur.fetchone()

    report_rows = []
    report_summary = summarize_report_rows([])
    if latest:
        path = _resolve_upload_path(str(latest.get("stored_path")))
        if path is not None:
            cleaned = clean_file(path)
            if cleaned.get("ok"):
                upload_meta = {
                    "counterParty": latest.get("counter_party") or "",
                    "date": str(latest.get("eval_date") or ""),
                    "description": latest.get("description") or "",
                    "sourcefile": latest.get("original_name") or path.name,
                    "instrumentType": latest.get("instrument_type") or "",
                }
                report_rows = build_report_rows([cleaned], upload_meta=upload_meta, report_type=report_type)
                report_summary = summarize_report_rows(report_rows)

    if fmt == "json":
        payload = {
            "period": {"dateFrom": date_from, "dateTo": date_to},
            "reportType": report_type,
            "summary": report_summary,
            "rows": report_rows,
            "yieldCurve": load_yield_curve(),
        }
        body = json.dumps(payload, indent=2, default=str)
        return Response(
            body,
            mimetype="application/json; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="valuation-report.json"'
            },
        )

    if fmt != "csv":
        return jsonify({"error": "unsupported format; use csv or json"}), 400

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Dura Capital — Loan report export"])
    w.writerow(["Report type", report_type])
    w.writerow(["Period from", date_from, "to", date_to])
    w.writerow([])
    w.writerow(["Summary", "Value"])
    for k, v in report_summary.items():
        w.writerow([k, v])
    w.writerow([])
    w.writerow(["Report preview rows"])
    w.writerow(
        [
            "pricing_date",
            "creator",
            "current_balance",
            "yield",
            "duration",
            "sourcefile",
            "description",
            "loanvalue",
            "loan_number",
            "price",
            "discount_rate",
            "days_to_maturity",
        ]
    )
    for i in report_rows:
        w.writerow(
            [
                i.get("pricing_date"),
                i.get("creator"),
                i.get("current_balance"),
                i.get("yield"),
                i.get("duration"),
                i.get("sourcefile"),
                i.get("description"),
                i.get("loanvalue"),
                i.get("loan_number"),
                i.get("price"),
                i.get("discount_rate"),
                i.get("days_to_maturity"),
            ]
        )

    return Response(
        out.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="valuation-report.csv"'},
    )


@app.route("/api/yield-curve", methods=["GET"])
@require_auth
def get_yield_curve():
    """Get current yield curve data with calculations."""
    try:
        days_back = request.args.get("days_back", 30, type=int)
        data = get_yield_curve_data(days_back=days_back)
        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/yield-curve/metrics", methods=["GET"])
@require_auth
def get_yield_curve_metrics():
    """Get yield curve metrics and calculations."""
    try:
        client = StLouisFedClient()
        yield_data = client.get_yield_curve_rates()
        metrics = client.calculate_yield_curve_metrics(yield_data)
        
        return jsonify({
            "success": True,
            "data": metrics
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/yield-curve/series/<series_id>", methods=["GET"])
@require_auth
def get_treasury_series(series_id):
    """Get specific Treasury series data."""
    try:
        client = StLouisFedClient()
        observation_start = request.args.get("start")
        observation_end = request.args.get("end")
        
        data = client.get_yield_curve_rates(observation_start, observation_end)
        
        if series_id in data:
            return jsonify({
                "success": True,
                "data": data[series_id]
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Series {series_id} not found"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
