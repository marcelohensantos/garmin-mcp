import json

from tools.calendar import delete_workout, get_scheduled_workouts, get_workouts, schedule_workout


def test_schedule_workout(garmin_mock):
    result = json.loads(schedule_workout("99999", "2026-05-15"))
    assert result["scheduledWorkoutId"] == 11111
    garmin_mock.schedule_workout.assert_called_once_with("99999", "2026-05-15")


def test_get_workouts(garmin_mock):
    result = json.loads(get_workouts(10))
    assert isinstance(result, list)
    assert result[0]["workoutId"] == 99999
    garmin_mock.get_workouts.assert_called_once_with(0, 10)


def test_delete_workout(garmin_mock):
    result = json.loads(delete_workout("99999"))
    assert result["deleted"] == "99999"
    garmin_mock.delete_workout.assert_called_once_with("99999")


def test_get_scheduled_workouts_returns_sorted(garmin_mock):
    result = json.loads(get_scheduled_workouts("2026-05-11", "2026-05-17"))
    assert isinstance(result, list)
    assert result[0]["date"] == "2026-05-13"
    assert result[0]["workoutName"] == "Threshold 3x14min"
    assert result[0]["sportType"] == "running"
    assert result[1]["date"] == "2026-05-15"


def test_get_scheduled_workouts_filters_by_date(garmin_mock):
    result = json.loads(get_scheduled_workouts("2026-05-14", "2026-05-17"))
    assert len(result) == 1
    assert result[0]["date"] == "2026-05-15"


def test_get_scheduled_workouts_invalid_date(garmin_mock):
    assert "error" in json.loads(get_scheduled_workouts("2026-13-01", "2026-05-17"))


def test_get_scheduled_workouts_start_after_end(garmin_mock):
    assert "error" in json.loads(get_scheduled_workouts("2026-05-17", "2026-05-11"))
