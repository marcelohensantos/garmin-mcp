import json

import auth
from app import mcp
from utils import today


@mcp.tool()
def get_stats(target_date: str | None = None) -> str:
    """Return daily stats (steps, calories, floors, etc.) for target_date (YYYY-MM-DD)."""
    data = auth.get_client().get_stats(target_date or today())
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_heart_rates(target_date: str | None = None) -> str:
    """Return heart-rate data for target_date (YYYY-MM-DD)."""
    data = auth.get_client().get_heart_rates(target_date or today())
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_sleep(target_date: str | None = None) -> str:
    """Return sleep data for the night ending on target_date (YYYY-MM-DD)."""
    data = auth.get_client().get_sleep_data(target_date or today())
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_stress(target_date: str | None = None) -> str:
    """Return stress data for target_date (YYYY-MM-DD)."""
    data = auth.get_client().get_stress_data(target_date or today())
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_body_battery(target_date: str | None = None) -> str:
    """Return Body Battery data for target_date (YYYY-MM-DD)."""
    d = target_date or today()
    data = auth.get_client().get_body_battery(d, d)
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_body_composition(target_date: str | None = None) -> str:
    """Return body composition (weight, BMI, etc.) for target_date (YYYY-MM-DD)."""
    data = auth.get_client().get_body_composition(target_date or today())
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_hrv_data(target_date: str | None = None) -> str:
    """Return HRV (Heart Rate Variability) data for target_date (YYYY-MM-DD)."""
    data = auth.get_client().get_hrv_data(target_date or today())
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_spo2(target_date: str | None = None) -> str:
    """Return SpO2 (blood oxygen) data for target_date (YYYY-MM-DD)."""
    data = auth.get_client().get_spo2_data(target_date or today())
    return json.dumps(data, default=str, indent=2)
