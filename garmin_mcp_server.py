import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("Garmin Connect")

_client: Garmin | None = None


def get_client() -> Garmin:
    global _client
    if _client is not None:
        return _client

    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    if not email or not password:
        raise RuntimeError("GARMIN_EMAIL and GARMIN_PASSWORD must be set in .env")

    token_store = Path.home() / ".garminconnect"
    token_store.mkdir(exist_ok=True)
    token_file = token_store / "oauth_tokens.json"

    client = Garmin(email=email, password=password, return_on_mfa=False)

    if token_file.exists():
        client.login(token_file.read_text())
    else:
        client.login()
        token_file.write_text(client.garth.dumps())

    _client = client
    return _client


def _today() -> str:
    return date.today().isoformat()


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------


@mcp.tool()
def get_activities(limit: int = 20) -> str:
    """Return the most recent activities."""
    activities = get_client().get_activities(0, limit)
    return json.dumps(activities, default=str, indent=2)


@mcp.tool()
def get_activities_by_date(start_date: str, end_date: str | None = None) -> str:
    """Return activities between start_date and end_date (YYYY-MM-DD). End defaults to today."""
    end = end_date or _today()
    activities = get_client().get_activities_by_date(start_date, end)
    return json.dumps(activities, default=str, indent=2)


@mcp.tool()
def get_activity_details(activity_id: str) -> str:
    """Return full details for a single activity by its ID."""
    details = get_client().get_activity_details(activity_id)
    return json.dumps(details, default=str, indent=2)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------


@mcp.tool()
def export_activity(activity_id: str, fmt: str = "gpx") -> str:
    """
    Export a single activity file. fmt options: gpx, tcx, fit, csv.
    Returns the file path where the export was saved.
    """
    fmt = fmt.lower()
    client = get_client()
    export_dir = Path.home() / "garmin_exports"
    export_dir.mkdir(exist_ok=True)

    if fmt == "gpx":
        data = client.download_activity(activity_id, dl_fmt=client.ActivityDownloadFormat.GPX)
        ext = "gpx"
    elif fmt == "tcx":
        data = client.download_activity(activity_id, dl_fmt=client.ActivityDownloadFormat.TCX)
        ext = "tcx"
    elif fmt == "fit":
        data = client.download_activity(activity_id, dl_fmt=client.ActivityDownloadFormat.ORIGINAL)
        ext = "zip"
    elif fmt == "csv":
        data = client.download_activity(activity_id, dl_fmt=client.ActivityDownloadFormat.CSV)
        ext = "csv"
    else:
        return json.dumps({"error": f"Unknown format: {fmt}. Use gpx, tcx, fit, or csv."})

    out_path = export_dir / f"{activity_id}.{ext}"
    out_path.write_bytes(data)
    return json.dumps({"path": str(out_path), "bytes": len(data)})


@mcp.tool()
def export_activities_csv(start_date: str, end_date: str | None = None) -> str:
    """Export a summary CSV of activities between start_date and end_date."""
    import csv
    import io

    end = end_date or _today()
    activities = get_client().get_activities_by_date(start_date, end)

    if not activities:
        return json.dumps({"message": "No activities found for the given range."})

    keys = list(activities[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(activities)

    export_dir = Path.home() / "garmin_exports"
    export_dir.mkdir(exist_ok=True)
    out_path = export_dir / f"activities_{start_date}_{end}.csv"
    out_path.write_text(buf.getvalue(), encoding="utf-8")
    return json.dumps({"path": str(out_path), "rows": len(activities)})


# ---------------------------------------------------------------------------
# Health & wellness
# ---------------------------------------------------------------------------


@mcp.tool()
def get_stats(target_date: str | None = None) -> str:
    """Return daily stats (steps, calories, floors, etc.) for target_date (YYYY-MM-DD)."""
    d = target_date or _today()
    data = get_client().get_stats(d)
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_heart_rates(target_date: str | None = None) -> str:
    """Return heart-rate data for target_date (YYYY-MM-DD)."""
    d = target_date or _today()
    data = get_client().get_heart_rates(d)
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_sleep(target_date: str | None = None) -> str:
    """Return sleep data for the night ending on target_date (YYYY-MM-DD)."""
    d = target_date or _today()
    data = get_client().get_sleep_data(d)
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_stress(target_date: str | None = None) -> str:
    """Return stress data for target_date (YYYY-MM-DD)."""
    d = target_date or _today()
    data = get_client().get_stress_data(d)
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_body_battery(target_date: str | None = None) -> str:
    """Return Body Battery data for target_date (YYYY-MM-DD)."""
    d = target_date or _today()
    start = d
    end = d
    data = get_client().get_body_battery(start, end)
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_body_composition(target_date: str | None = None) -> str:
    """Return body composition (weight, BMI, etc.) for target_date (YYYY-MM-DD)."""
    d = target_date or _today()
    data = get_client().get_body_composition(d)
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_hrv_data(target_date: str | None = None) -> str:
    """Return HRV (Heart Rate Variability) data for target_date (YYYY-MM-DD)."""
    d = target_date or _today()
    data = get_client().get_hrv_data(d)
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_spo2(target_date: str | None = None) -> str:
    """Return SpO2 (blood oxygen) data for target_date (YYYY-MM-DD)."""
    d = target_date or _today()
    data = get_client().get_spo2_data(d)
    return json.dumps(data, default=str, indent=2)


# ---------------------------------------------------------------------------
# Training & fitness
# ---------------------------------------------------------------------------


@mcp.tool()
def get_training_status(target_date: str | None = None) -> str:
    """Return training status and load for target_date (YYYY-MM-DD)."""
    d = target_date or _today()
    data = get_client().get_training_status(d)
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_personal_records() -> str:
    """Return all personal records (PRs) for the authenticated user."""
    user_id = get_client().get_full_name()
    data = get_client().get_personal_record()
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_vo2max() -> str:
    """Return VO2 max estimates."""
    data = get_client().get_max_metrics(_today())
    return json.dumps(data, default=str, indent=2)


# ---------------------------------------------------------------------------
# Profile & devices
# ---------------------------------------------------------------------------


@mcp.tool()
def get_user_profile() -> str:
    """Return the user's Garmin profile information."""
    data = get_client().get_user_profile()
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_devices() -> str:
    """Return the list of devices linked to the Garmin account."""
    data = get_client().get_devices()
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_gear() -> str:
    """Return the gear (shoes, bikes, etc.) associated with the account."""
    user_id = get_client().get_full_name()
    data = get_client().get_gear(get_client().profile["userName"])
    return json.dumps(data, default=str, indent=2)


if __name__ == "__main__":
    mcp.run()
