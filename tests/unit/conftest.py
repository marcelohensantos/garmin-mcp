from unittest.mock import MagicMock, patch

import pytest


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
    mock.upload_workout.return_value          = {"workoutId": 99999, "workoutName": "Test Workout"}
    mock.upload_swimming_workout.return_value = {"workoutId": 77777, "workoutName": "Test Swim"}
    mock.upload_strength_workout              = mock.upload_workout  # alias for strength tests
    mock.schedule_workout.return_value = {"scheduledWorkoutId": 11111, "date": "2026-05-15"}
    mock.get_workouts.return_value = [{"workoutId": 99999, "workoutName": "Test Workout"}]
    mock.delete_workout.return_value = None
    mock.get_scheduled_workouts.return_value = [
        {
            "date": "2026-05-13",
            "workoutId": 99999,
            "workoutName": "Threshold 3x14min",
            "sportTypeKey": "running",
        },
        {
            "date": "2026-05-15",
            "workoutId": 88888,
            "workoutName": "Long Run",
            "sportTypeKey": "running",
        },
    ]

    import cache
    cache.invalidate()
    with patch("auth.get_client", return_value=mock):
        yield mock
    cache.invalidate()
# note: save_plan uses real filesystem via tmp_path; no mock needed
