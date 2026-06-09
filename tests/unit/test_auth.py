import pytest

import auth as auth_module


@pytest.fixture(autouse=True)
def reset_client(monkeypatch):
    monkeypatch.setattr(auth_module, "_client", None)


def test_missing_email_raises(monkeypatch):
    monkeypatch.delenv("GARMIN_EMAIL", raising=False)
    monkeypatch.delenv("GARMIN_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="GARMIN_EMAIL"):
        auth_module.get_client()


def test_missing_password_raises(monkeypatch):
    monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
    monkeypatch.delenv("GARMIN_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="GARMIN_PASSWORD"):
        auth_module.get_client()


def test_returns_cached_client(monkeypatch):
    from unittest.mock import MagicMock
    fake = MagicMock()
    monkeypatch.setattr(auth_module, "_client", fake)
    assert auth_module.get_client() is fake


def test_with_retry_retries_then_succeeds(monkeypatch):
    from requests.exceptions import ConnectionError as ReqConnError
    monkeypatch.setattr(auth_module.time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise ReqConnError("('Connection aborted.', RemoteDisconnected())")
        return "ok"

    assert auth_module._with_retry(flaky)() == "ok"
    assert calls["n"] == 2


def test_with_retry_reraises_after_max(monkeypatch):
    from requests.exceptions import ConnectionError as ReqConnError
    monkeypatch.setattr(auth_module.time, "sleep", lambda *_: None)

    def always_fail():
        raise ReqConnError("dead socket")

    with pytest.raises(ReqConnError):
        auth_module._with_retry(always_fail)()


def test_retry_client_wraps_nested_client(monkeypatch):
    from unittest.mock import MagicMock
    from requests.exceptions import ConnectionError as ReqConnError
    monkeypatch.setattr(auth_module.time, "sleep", lambda *_: None)

    target = MagicMock()
    calls = {"n": 0}

    def put(*a, **k):
        calls["n"] += 1
        if calls["n"] < 2:
            raise ReqConnError("Connection aborted")
        return "done"

    target.client.put.side_effect = put
    proxy = auth_module._RetryClient(target)
    assert proxy.client.put("connectapi", "/x") == "done"
    assert calls["n"] == 2
