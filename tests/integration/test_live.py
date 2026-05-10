"""
Integration tests against the real Garmin Connect API.

Run with:
    GARMIN_INTEGRATION=1 pytest tests/integration/ -v
"""

import json
import os

import pytest

from auth import get_client


@pytest.fixture(scope="module", autouse=True)
def require_integration():
    if not os.getenv("GARMIN_INTEGRATION"):
        pytest.skip("set GARMIN_INTEGRATION=1 to run live tests")


@pytest.fixture(scope="module")
def client():
    return get_client()


# ---------------------------------------------------------------------------
# Connectivity
# ---------------------------------------------------------------------------


def test_authenticated(client):
    profile = client.get_user_profile()
    assert isinstance(profile, dict)
    assert "id" in profile


def test_devices_returns_list(client):
    devices = client.get_devices()
    assert isinstance(devices, list)
    assert len(devices) > 0
    assert "productDisplayName" in devices[0]


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------


def test_get_activities_shape(client):
    activities = client.get_activities(0, 1)
    assert isinstance(activities, list)
    assert len(activities) > 0
    first = activities[0]
    assert "activityId" in first
    assert "activityName" in first
    assert "startTimeLocal" in first


def test_get_activities_by_date_shape(client):
    activities = client.get_activities_by_date("2026-01-01", "2026-12-31")
    assert isinstance(activities, list)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_get_stats_shape(client):
    from utils import today
    data = client.get_stats(today())
    assert isinstance(data, dict)
    assert "totalSteps" in data


def test_get_heart_rates_shape(client):
    from utils import today
    data = client.get_heart_rates(today())
    assert isinstance(data, dict)
    assert "restingHeartRate" in data


def test_get_sleep_shape(client):
    from utils import today
    data = client.get_sleep_data(today())
    assert isinstance(data, dict)
    assert "dailySleepDTO" in data


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def test_get_personal_records_shape(client):
    records = client.get_personal_record()
    assert isinstance(records, list)


def test_get_vo2max_shape(client):
    from utils import today
    data = client.get_max_metrics(today())
    assert isinstance(data, (dict, list))
