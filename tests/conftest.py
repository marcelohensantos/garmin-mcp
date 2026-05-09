import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def garmin_mock():
    mock = MagicMock()

    mock.get_activities.return_value = [
        {"activityId": "123456789", "activityName": "Morning Run", "distance": 10000.0}
    ]
    mock.get_activities_by_date.return_value = [
        {"activityId": "123456789", "activityName": "Morning Run", "distance": 10000.0}
    ]
    mock.get_activity_details.return_value = {"activityId": "123456789", "laps": []}
    mock.download_activity.return_value = b"<gpx>fake data</gpx>"
    mock.get_stats.return_value = {"totalSteps": 8000, "totalKilocalories": 2100}
    mock.get_heart_rates.return_value = {"restingHeartRate": 52, "heartRateValues": []}
    mock.get_sleep_data.return_value = {"dailySleepDTO": {"sleepTimeSeconds": 28800}}
    mock.get_stress_data.return_value = {"avgStressLevel": 28, "stressChartValueOffset": 0}
    mock.get_body_battery.return_value = [{"charged": 85, "drained": 42}]
    mock.get_body_composition.return_value = {"startDate": "2024-01-15", "weight": 75.0}
    mock.get_hrv_data.return_value = {"hrvSummary": {"weeklyAvg": 48}}
    mock.get_spo2_data.return_value = {"averageSpO2": 97}
    mock.get_training_status.return_value = {"trainingStatus": "Maintaining"}
    mock.get_personal_record.return_value = [{"typeId": 1, "value": 42.0}]
    mock.get_max_metrics.return_value = {"vo2MaxPreciseValue": 52.3}
    mock.get_user_profile.return_value = {"userName": "testuser", "displayName": "Test User"}
    mock.get_devices.return_value = [{"deviceId": 9999, "productDisplayName": "Forerunner 965"}]
    mock.profile = {"userName": "testuser"}
    mock.get_gear.return_value = [{"gearPk": 1, "customMakeModel": "Nike Vomero"}]

    with patch("auth.get_client", return_value=mock):
        yield mock
