import json

import auth
from app import mcp
from utils import today


@mcp.tool()
def get_training_status(target_date: str | None = None) -> str:
    """Return training status and load for target_date (YYYY-MM-DD)."""
    data = auth.get_client().get_training_status(target_date or today())
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_personal_records() -> str:
    """Return all personal records (PRs) for the authenticated user."""
    data = auth.get_client().get_personal_record()
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_vo2max() -> str:
    """Return VO2 max estimates."""
    data = auth.get_client().get_max_metrics(today())
    return json.dumps(data, default=str, indent=2)
