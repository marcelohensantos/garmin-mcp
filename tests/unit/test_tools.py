import json
from unittest.mock import patch

from tools.activities import (
    export_activities_csv,
    export_activity,
    get_activities,
    get_activities_by_date,
)
from tools.health import get_body_battery, get_stats
from tools.profile import get_gear
from utils import today as _today

# ---------------------------------------------------------------------------
# Activities — filter logic
# ---------------------------------------------------------------------------


def test_get_activities_by_date_defaults_end_to_today(garmin_mock):
    get_activities_by_date("2024-01-01")
    garmin_mock.get_activities_by_date.assert_called_once_with("2024-01-01", _today())


def test_get_activities_filters_by_type(garmin_mock):
    garmin_mock.get_activities.return_value = [
        {"activityId": "1", "activityType": {"typeKey": "running"}},
        {"activityId": "2", "activityType": {"typeKey": "fitness_equipment"}},
        {"activityId": "3", "activityType": {"typeKey": "swimming"}},
    ]
    result = json.loads(get_activities(limit=10, activity_type="running"))
    assert len(result) == 1
    assert result[0]["activityId"] == "1"


def test_get_activities_by_date_filters_by_type(garmin_mock):
    garmin_mock.get_activities_by_date.return_value = [
        {"activityId": "1", "activityType": {"typeKey": "running"}},
        {"activityId": "2", "activityType": {"typeKey": "fitness_equipment"}},
    ]
    result = json.loads(get_activities_by_date("2026-01-01", activity_type="fitness_equipment"))
    assert len(result) == 1
    assert result[0]["activityId"] == "2"


def test_get_activities_filter_case_insensitive(garmin_mock):
    garmin_mock.get_activities.return_value = [
        {"activityId": "1", "activityType": {"typeKey": "Running"}},
    ]
    result = json.loads(get_activities(limit=5, activity_type="RUNNING"))
    assert len(result) == 1


def test_get_activities_no_filter_returns_all(garmin_mock):
    garmin_mock.get_activities.return_value = [
        {"activityId": "1", "activityType": {"typeKey": "running"}},
        {"activityId": "2", "activityType": {"typeKey": "swimming"}},
    ]
    result = json.loads(get_activities(limit=10))
    assert len(result) == 2


# ---------------------------------------------------------------------------
# Exports — real I/O behaviour
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
# Health — non-trivial param behaviour
# ---------------------------------------------------------------------------


def test_get_stats_defaults_to_today(garmin_mock):
    get_stats()
    garmin_mock.get_stats.assert_called_once_with(_today())


def test_get_body_battery_passes_same_date_twice(garmin_mock):
    get_body_battery("2024-01-15")
    garmin_mock.get_body_battery.assert_called_once_with("2024-01-15", "2024-01-15")


# ---------------------------------------------------------------------------
# Profile — non-trivial param behaviour
# ---------------------------------------------------------------------------


def test_get_gear_uses_profile_username(garmin_mock):
    get_gear()
    garmin_mock.get_gear.assert_called_once_with("testuser")
