"""Typed exception hierarchy for Garmin API errors."""
from __future__ import annotations

import contextlib
import json

from garminconnect import GarminConnectAuthenticationError, GarminConnectTooManyRequestsError


class GarminAPIError(Exception):
    pass


class GarminAuthError(GarminAPIError):
    pass


class GarminRateLimitError(GarminAPIError):
    pass


class GarminNotFoundError(GarminAPIError):
    pass


def _translate(exc: Exception) -> GarminAPIError:
    if isinstance(exc, GarminConnectAuthenticationError):
        return GarminAuthError(str(exc))
    if isinstance(exc, GarminConnectTooManyRequestsError):
        return GarminRateLimitError(str(exc))
    try:
        from garth.exc import GarthHTTPError  # optional dep
        if isinstance(exc, GarthHTTPError) and exc.response is not None:
            code = exc.response.status_code
            if code in (401, 403):
                return GarminAuthError(str(exc))
            if code == 404:
                return GarminNotFoundError(str(exc))
            if code == 429:
                return GarminRateLimitError(str(exc))
    except ImportError:
        pass
    return GarminAPIError(str(exc))


@contextlib.contextmanager
def api_call():
    """Translate garminconnect exceptions to typed GarminAPIError subclasses."""
    try:
        yield
    except GarminAPIError:
        raise
    except (GarminConnectAuthenticationError, GarminConnectTooManyRequestsError, Exception) as exc:
        raise _translate(exc) from exc


def tool_guard(fn):
    """Decorator: catch GarminAPIError inside a tool and return a JSON error string."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except GarminAuthError as e:
            return json.dumps({"error": str(e), "type": "auth_error"})
        except GarminRateLimitError as e:
            return json.dumps({"error": str(e), "type": "rate_limit"})
        except GarminNotFoundError as e:
            return json.dumps({"error": str(e), "type": "not_found"})
        except GarminAPIError as e:
            return json.dumps({"error": str(e), "type": "api_error"})

    return wrapper
