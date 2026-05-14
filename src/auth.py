import os
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin

load_dotenv()

_client: Garmin | None = None
_TOKEN_STORE = Path(os.getenv("GARMIN_TOKEN_STORE", str(Path.home() / ".garminconnect")))


def get_client() -> Garmin:
    global _client
    if _client is not None:
        return _client

    email = os.getenv("GARMIN_EMAIL")
    if not email:
        raise RuntimeError("GARMIN_EMAIL is not set")

    password = os.getenv("GARMIN_PASSWORD")
    if not password:
        raise RuntimeError("GARMIN_PASSWORD is not set")

    _TOKEN_STORE.mkdir(exist_ok=True)

    from errors import GarminAuthError
    try:
        client = Garmin(email=email, password=password, return_on_mfa=False)
        client.login(str(_TOKEN_STORE))
    except Exception as exc:
        raise GarminAuthError(f"Login failed: {exc}") from exc

    _client = client
    return _client
