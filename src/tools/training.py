import auth
from app import mcp
from cache import cached
from utils import serialize, today


@mcp.tool()
@cached(ttl_seconds=300)
def get_training_status(target_date: str | None = None) -> str:
    """Return training status and load for target_date (YYYY-MM-DD)."""
    return serialize(auth.get_client().get_training_status(target_date or today()))


@mcp.tool()
@cached(ttl_seconds=600)
def get_personal_records() -> str:
    """Return all personal records (PRs) for the authenticated user."""
    return serialize(auth.get_client().get_personal_record())


@mcp.tool()
@cached(ttl_seconds=300)
def get_vo2max() -> str:
    """Return VO2 max estimates."""
    return serialize(auth.get_client().get_max_metrics(today()))
