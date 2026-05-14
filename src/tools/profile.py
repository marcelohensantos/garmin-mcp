import auth
from app import mcp
from cache import cached
from utils import serialize


@mcp.tool()
@cached(ttl_seconds=600)
def get_user_profile() -> str:
    """Return the user's Garmin profile information."""
    return serialize(auth.get_client().get_user_profile())


@mcp.tool()
@cached(ttl_seconds=600)
def get_devices() -> str:
    """Return the list of devices linked to the Garmin account."""
    return serialize(auth.get_client().get_devices())


@mcp.tool()
@cached(ttl_seconds=600)
def get_gear() -> str:
    """Return the gear (shoes, bikes, etc.) associated with the account."""
    client = auth.get_client()
    return serialize(client.get_gear(client.profile["userName"]))
