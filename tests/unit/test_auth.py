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
