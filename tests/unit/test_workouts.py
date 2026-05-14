import json

import pytest

from tools.workouts import (
    _pace_target,
    create_running_workout,
    delete_workout,
    get_scheduled_workouts,
    get_workouts,
    schedule_workout,
    update_running_workout,
)


# ---------------------------------------------------------------------------
# Pace helper
# ---------------------------------------------------------------------------


def test_pace_target_type_is_pace_zone():
    t = _pace_target("4:31")
    assert t["targetType"]["workoutTargetTypeId"] == 6
    assert t["targetType"]["workoutTargetTypeKey"] == "pace.zone"


def test_pace_target_values_in_meters_per_second():
    # 4:31 = 271 s/km; tolerance ±10 s → fast=261s/km, slow=281s/km (in m/s)
    t = _pace_target("4:31", tolerance_sec=10)
    assert abs(t["targetValueOne"] - round(1000 / 261, 7)) < 1e-5  # fast bound m/s
    assert abs(t["targetValueTwo"] - round(1000 / 281, 7)) < 1e-5  # slow bound m/s
    assert t["targetValueOne"] > t["targetValueTwo"]  # fast > slow in m/s


# ---------------------------------------------------------------------------
# create_running_workout
# ---------------------------------------------------------------------------


_THRESHOLD_WORKOUT = json.dumps({
    "name": "Threshold 3x14min",
    "warmup_minutes": 15,
    "main_set": [
        {"type": "interval", "minutes": 14, "pace": "4:31"},
        {"type": "recovery", "minutes": 2},
    ],
    "repeat": 3,
    "cooldown_minutes": 10,
})


def test_create_running_workout_returns_id(garmin_mock):
    result = json.loads(create_running_workout(_THRESHOLD_WORKOUT))
    assert result["workoutId"] == 99999
    assert result["name"] == "Threshold 3x14min"
    garmin_mock.upload_workout.assert_called_once()


def test_create_running_workout_invalid_json(garmin_mock):
    result = json.loads(create_running_workout("not json"))
    assert "error" in result


def test_create_running_workout_no_pace(garmin_mock):
    spec = json.dumps({
        "name": "Easy Run",
        "warmup_minutes": 10,
        "main_set": [{"type": "interval", "minutes": 30}],
        "repeat": 1,
        "cooldown_minutes": 10,
    })
    result = json.loads(create_running_workout(spec))
    assert result["workoutId"] == 99999


def test_simple_easy_merges_into_one_step(garmin_mock):
    """Single no-pace interval: warmup + run + cooldown collapsed into one step + lap cooldown."""
    spec = json.dumps({
        "name": "Easy 30",
        "warmup_minutes": 5,
        "main_set": [{"type": "interval", "minutes": 30}],
        "repeat": 1,
        "cooldown_minutes": 5,
    })
    create_running_workout(spec)
    call_args = garmin_mock.upload_workout.call_args[0][0]
    steps = call_args["workoutSegments"][0]["workoutSteps"]
    assert len(steps) == 2
    assert steps[0]["endConditionValue"] == 40 * 60  # 5+30+5 merged
    assert steps[1]["endCondition"]["conditionTypeKey"] == "lap.button"
    assert steps[1]["endConditionValue"] is None


def test_complex_workout_ends_with_lap_cooldown(garmin_mock):
    """Structured workout: warmup + main set + lap-button cooldown (no time-based cooldown)."""
    create_running_workout(_THRESHOLD_WORKOUT)
    call_args = garmin_mock.upload_workout.call_args[0][0]
    steps = call_args["workoutSegments"][0]["workoutSteps"]
    last = steps[-1]
    assert last["endCondition"]["conditionTypeKey"] == "lap.button"
    assert last["endConditionValue"] is None


_STRIDES_WORKOUT = json.dumps({
    "name": "Easy + Strides",
    "warmup_minutes": 10,
    "main_set": [
        {"type": "interval", "minutes": 20},
        {
            "type": "repeat",
            "repeat": 6,
            "steps": [
                {"type": "interval", "seconds": 20, "pace": "3:54"},
                {"type": "recovery", "minutes": 1, "seconds": 40},
            ],
        },
    ],
    "repeat": 1,
    "cooldown_minutes": 5,
})


def test_nested_repeat_group_is_created(garmin_mock):
    """Nested repeat block produces a RepeatGroupDTO step (not flat stride steps)."""
    result = json.loads(create_running_workout(_STRIDES_WORKOUT))
    assert result["workoutId"] == 99999

    call_args = garmin_mock.upload_workout.call_args[0][0]
    steps = call_args["workoutSegments"][0]["workoutSteps"]
    # warmup, easy interval, repeat group, lap cooldown
    assert len(steps) == 4
    repeat_group = steps[2]
    assert repeat_group["numberOfIterations"] == 6
    assert len(repeat_group["workoutSteps"]) == 2


# ---------------------------------------------------------------------------
# update_running_workout
# ---------------------------------------------------------------------------


def test_update_running_workout_calls_put(garmin_mock):
    """update_running_workout should PUT, not POST, and return updated: true."""
    spec = json.dumps({
        "name": "Limiar — 3×14' T",
        "warmup_km": 2,
        "warmup_pace": ["5:26", "5:59"],
        "main_set": [
            {"type": "repeat", "repeat": 3, "steps": [
                {"type": "interval", "minutes": 14, "pace": "4:31"},
                {"type": "recovery", "minutes": 2},
            ]}
        ],
        "cooldown_km": 1,
        "cooldown_pace": ["5:26", "5:59"],
        "pace_tolerance_sec": 5,
    })
    result = json.loads(update_running_workout("99999", spec))
    assert result["updated"] is True
    assert result["workoutId"] == 99999
    garmin_mock.client.put.assert_called_once()
    garmin_mock.upload_workout.assert_not_called()


def test_update_running_workout_invalid_json(garmin_mock):
    result = json.loads(update_running_workout("99999", "bad json"))
    assert "error" in result


# ---------------------------------------------------------------------------
# schedule_workout
# ---------------------------------------------------------------------------


def test_schedule_workout(garmin_mock):
    result = json.loads(schedule_workout("99999", "2026-05-15"))
    assert result["scheduledWorkoutId"] == 11111
    garmin_mock.schedule_workout.assert_called_once_with("99999", "2026-05-15")


# ---------------------------------------------------------------------------
# get_workouts
# ---------------------------------------------------------------------------


def test_get_workouts(garmin_mock):
    result = json.loads(get_workouts(10))
    assert isinstance(result, list)
    assert result[0]["workoutId"] == 99999
    garmin_mock.get_workouts.assert_called_once_with(0, 10)


# ---------------------------------------------------------------------------
# delete_workout
# ---------------------------------------------------------------------------


def test_delete_workout(garmin_mock):
    result = json.loads(delete_workout("99999"))
    assert result["deleted"] == "99999"
    garmin_mock.delete_workout.assert_called_once_with("99999")


# ---------------------------------------------------------------------------
# get_scheduled_workouts
# ---------------------------------------------------------------------------


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
    result = json.loads(get_scheduled_workouts("2026-13-01", "2026-05-17"))
    assert "error" in result


def test_get_scheduled_workouts_start_after_end(garmin_mock):
    result = json.loads(get_scheduled_workouts("2026-05-17", "2026-05-11"))
    assert "error" in result
