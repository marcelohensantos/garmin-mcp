import json

import auth
from app import mcp


@mcp.tool()
def get_user_profile() -> str:
    """Return the user's Garmin profile information."""
    data = auth.get_client().get_user_profile()
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_devices() -> str:
    """Return the list of devices linked to the Garmin account."""
    data = auth.get_client().get_devices()
    return json.dumps(data, default=str, indent=2)


@mcp.tool()
def get_gear() -> str:
    """Return the gear (shoes, bikes, etc.) associated with the account."""
    client = auth.get_client()
    data = client.get_gear(client.profile["userName"])
    return json.dumps(data, default=str, indent=2)
