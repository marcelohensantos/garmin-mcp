"""MCP Resources — persistent context the LLM can read without calling a tool."""
import auth
from app import mcp
from cache import cached
from utils import serialize, today


@mcp.resource("garmin://athlete/profile")
@cached(ttl_seconds=600)
def athlete_profile() -> str:
    """Athlete profile: name, display name, unit preferences, and personal records."""
    client = auth.get_client()
    profile = client.get_user_profile()
    records = client.get_personal_record()
    return serialize({"profile": profile, "personal_records": records})


@mcp.resource("garmin://health/today")
@cached(ttl_seconds=300)
def health_today() -> str:
    """Today's health snapshot: stats, Body Battery, HRV, sleep, and resting heart rate."""
    client  = auth.get_client()
    date    = today()
    stats   = client.get_stats(date)
    battery = client.get_body_battery(date, date)
    hrv     = client.get_hrv_data(date)
    sleep   = client.get_sleep_data(date)
    return serialize({
        "date":         date,
        "stats":        stats,
        "body_battery": battery,
        "hrv":          hrv,
        "sleep":        sleep,
    })
