import functools
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin
from requests.exceptions import ConnectionError as _ReqConnError

load_dotenv()

_client = None
_TOKEN_STORE = Path(os.getenv("GARMIN_TOKEN_STORE", str(Path.home() / ".garminconnect")))

# Garmin keeps HTTP keep-alive connections alive; idle sockets get closed
# server-side, so the next call can hit a dead socket → ConnectionError /
# RemoteDisconnected. These drops happen on send (the request never reaches the
# server), so retrying is safe — it just reopens the socket.
_RETRY_EXCEPTIONS: tuple = (_ReqConnError,)
try:
    from urllib3.exceptions import ProtocolError as _ProtocolError
    _RETRY_EXCEPTIONS = _RETRY_EXCEPTIONS + (_ProtocolError,)
except Exception:
    pass

_MAX_ATTEMPTS = 3
_BACKOFF_SEC = 0.6


def _with_retry(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        last_exc = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return fn(*args, **kwargs)
            except _RETRY_EXCEPTIONS as exc:
                last_exc = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(_BACKOFF_SEC * (attempt + 1))
        raise last_exc
    return wrapper


class _RetryClient:
    """Proxy around the Garmin client that retries calls on dropped connections.
    Wraps the nested .client (garth) too, so client.client.put(...) also retries."""

    def __init__(self, target):
        object.__setattr__(self, "_target", target)

    def __getattr__(self, name):
        attr = getattr(object.__getattribute__(self, "_target"), name)
        if name == "client":
            return _RetryClient(attr)
        if callable(attr):
            return _with_retry(attr)
        return attr


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

    _client = _RetryClient(client)
    return _client
