import json
from unittest.mock import patch

import pytest

from tools.activities import (
    export_activities_csv,
    export_activity,
    get_activities,
    get_activities_by_date,
    get_activity_details,
)
from tools.health import (
    get_body_battery,
    get_body_composition,
    get_heart_rates,
    get_hrv_data,
    get_sleep,
    get_spo2,
    get_stats,
    get_stress,
)
from tools.profile import get_devices, get_gear, get_user_profile
from tools.training import get_personal_records, get_training_status, get_vo2max
from utils import today as _today


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------


def test_get_activities_returns_list(garmin_mock):
    result = json.loads(get_activities(limit=5))
    assert isinstance(result, list)
    assert result[0]["activityId"] == "123456789"
    garmin_mock.get_activities.assert_called_once_with(0, 5)


def test_get_activities_by_date(garmin_mock):
    result = json.loads(get_activities_by_date("2024-01-01", "2024-01-31"))
    assert isinstance(result, list)
    garmin_mock.get_activities_by_date.assert_called_once_with("2024-01-01", "2024-01-31")


def test_get_activities_by_date_defaults_end_to_today(garmin_mock):
    get_activities_by_date("2024-01-01")
    garmin_mock.get_activities_by_date.assert_called_once_with("2024-01-01", _today())


def test_get_activity_details(garmin_mock):
    result = json.loads(get_activity_details("123456789"))
    assert result["activityId"] == "123456789"
    garmin_mock.get_activity_details.assert_called_once_with("123456789")


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------


def test_export_activity_gpx(garmin_mock, tmp_path):
    with patch("utils.Path.home", return_value=tmp_path):
        result = json.loads(export_activity("123456789", "gpx"))
    assert result["bytes"] == len(b"<gpx>fake data</gpx>")
    assert (tmp_path / "garmin_exports" / "123456789.gpx").exists()


def test_export_activity_unknown_format(garmin_mock):
    result = json.loads(export_activity("123456789", "xyz"))
    assert "error" in result


def test_export_activities_csv(garmin_mock, tmp_path):
    with patch("utils.Path.home", return_value=tmp_path):
        result = json.loads(export_activities_csv("2024-01-01", "2024-01-31"))
    assert result["rows"] == 1
    assert (tmp_path / "garmin_exports").exists()


def test_export_activities_csv_empty(garmin_mock):
    garmin_mock.get_activities_by_date.return_value = []
    result = json.loads(export_activities_csv("2024-01-01", "2024-01-31"))
    assert "message" in result


# ---------------------------------------------------------------------------
# Health & wellness
# ---------------------------------------------------------------------------


def test_get_stats(garmin_mock):
    result = json.loads(get_stats("2024-01-15"))
    assert result["totalSteps"] == 8000
    garmin_mock.get_stats.assert_called_once_with("2024-01-15")


def test_get_stats_defaults_to_today(garmin_mock):
    get_stats()
    garmin_mock.get_stats.assert_called_once_with(_today())


def test_get_heart_rates(garmin_mock):
    result = json.loads(get_heart_rates("2024-01-15"))
    assert result["restingHeartRate"] == 52


def test_get_sleep(garmin_mock):
    result = json.loads(get_sleep("2024-01-15"))
    assert "dailySleepDTO" in result


def test_get_stress(garmin_mock):
    result = json.loads(get_stress("2024-01-15"))
    assert result["avgStressLevel"] == 28


def test_get_body_battery(garmin_mock):
    result = json.loads(get_body_battery("2024-01-15"))
    assert isinstance(result, list)
    garmin_mock.get_body_battery.assert_called_once_with("2024-01-15", "2024-01-15")


def test_get_body_composition(garmin_mock):
    result = json.loads(get_body_composition("2024-01-15"))
    assert result["weight"] == 75.0


def test_get_hrv_data(garmin_mock):
    result = json.loads(get_hrv_data("2024-01-15"))
    assert result["hrvSummary"]["weeklyAvg"] == 48


def test_get_spo2(garmin_mock):
    result = json.loads(get_spo2("2024-01-15"))
    assert result["averageSpO2"] == 97


# ---------------------------------------------------------------------------
# Training & fitness
# ---------------------------------------------------------------------------


def test_get_training_status(garmin_mock):
    result = json.loads(get_training_status("2024-01-15"))
    assert result["trainingStatus"] == "Maintaining"


def test_get_personal_records(garmin_mock):
    result = json.loads(get_personal_records())
    assert isinstance(result, list)
    garmin_mock.get_personal_record.assert_called_once()


def test_get_vo2max(garmin_mock):
    result = json.loads(get_vo2max())
    assert result["vo2MaxPreciseValue"] == 52.3


# ---------------------------------------------------------------------------
# Profile & devices
# ---------------------------------------------------------------------------


def test_get_user_profile(garmin_mock):
    result = json.loads(get_user_profile())
    assert result["userName"] == "testuser"


def test_get_devices(garmin_mock):
    result = json.loads(get_devices())
    assert isinstance(result, list)
    assert result[0]["productDisplayName"] == "Forerunner 965"


def test_get_gear(garmin_mock):
    result = json.loads(get_gear())
    assert isinstance(result, list)
    garmin_mock.get_gear.assert_called_once_with("testuser")
