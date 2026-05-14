import json

from tools.running import _pace_target, create_running_workout, update_running_workout


# ---------------------------------------------------------------------------
# Pace helper
# ---------------------------------------------------------------------------

def test_pace_target_type_is_pace_zone():
    t = _pace_target("4:31", 10)
    assert t["targetType"]["workoutTargetTypeId"] == 6
    assert t["targetType"]["workoutTargetTypeKey"] == "pace.zone"


def test_pace_target_values_in_meters_per_second():
    # 4:31 = 271 s/km; ±10s → fast=261, slow=281 s/km
    t = _pace_target("4:31", 10)
    assert abs(t["targetValueOne"] - round(1000 / 261, 7)) < 1e-5
    assert abs(t["targetValueTwo"] - round(1000 / 281, 7)) < 1e-5
    assert t["targetValueOne"] > t["targetValueTwo"]


# ---------------------------------------------------------------------------
# create_running_workout
# ---------------------------------------------------------------------------

_THRESHOLD = json.dumps({
    "name": "Threshold 3x14min",
    "warmup_minutes": 15,
    "main_set": [
        {"type": "interval", "minutes": 14, "pace": "4:31"},
        {"type": "recovery", "minutes": 2},
    ],
    "repeat": 3,
    "cooldown_minutes": 10,
})


def test_create_returns_id(garmin_mock):
    result = json.loads(create_running_workout(_THRESHOLD))
    assert result["workoutId"] == 99999
    assert result["name"] == "Threshold 3x14min"
    garmin_mock.upload_workout.assert_called_once()


def test_create_invalid_json(garmin_mock):
    assert "error" in json.loads(create_running_workout("not json"))


def test_create_no_pace(garmin_mock):
    spec = json.dumps({
        "name": "Easy Run",
        "warmup_minutes": 10,
        "main_set": [{"type": "interval", "minutes": 30}],
        "repeat": 1,
        "cooldown_minutes": 10,
    })
    assert json.loads(create_running_workout(spec))["workoutId"] == 99999


def test_simple_easy_merges_into_one_step(garmin_mock):
    """Single no-pace interval: warmup + run + cooldown merged, then lap cooldown."""
    spec = json.dumps({
        "name": "Easy 30",
        "warmup_minutes": 5,
        "main_set": [{"type": "interval", "minutes": 30}],
        "repeat": 1,
        "cooldown_minutes": 5,
    })
    create_running_workout(spec)
    steps = garmin_mock.upload_workout.call_args[0][0]["workoutSegments"][0]["workoutSteps"]
    assert len(steps) == 2
    assert steps[0]["endConditionValue"] == 40 * 60
    assert steps[1]["endCondition"]["conditionTypeKey"] == "lap.button"
    assert steps[1]["endConditionValue"] is None


def test_complex_workout_ends_with_lap_cooldown(garmin_mock):
    create_running_workout(_THRESHOLD)
    steps = garmin_mock.upload_workout.call_args[0][0]["workoutSegments"][0]["workoutSteps"]
    assert steps[-1]["endCondition"]["conditionTypeKey"] == "lap.button"
    assert steps[-1]["endConditionValue"] is None


_STRIDES = json.dumps({
    "name": "Easy + Strides",
    "warmup_minutes": 10,
    "main_set": [
        {"type": "interval", "minutes": 20},
        {
            "type": "repeat", "repeat": 6,
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
    """Nested repeat block produces a RepeatGroupDTO (not flat steps)."""
    assert json.loads(create_running_workout(_STRIDES))["workoutId"] == 99999
    steps = garmin_mock.upload_workout.call_args[0][0]["workoutSegments"][0]["workoutSteps"]
    # warmup, easy interval, repeat group, lap cooldown
    assert len(steps) == 4
    rg = steps[2]
    assert rg["numberOfIterations"] == 6
    assert len(rg["workoutSteps"]) == 2


# ---------------------------------------------------------------------------
# update_running_workout
# ---------------------------------------------------------------------------

def test_update_calls_put_not_post(garmin_mock):
    spec = json.dumps({
        "name": "Limiar — 3×14' T",
        "warmup_km": 2, "warmup_pace": ["5:26", "5:59"],
        "main_set": [{"type": "repeat", "repeat": 3, "steps": [
            {"type": "interval", "minutes": 14, "pace": "4:31"},
            {"type": "recovery", "minutes": 2},
        ]}],
        "cooldown_km": 1, "cooldown_pace": ["5:26", "5:59"],
        "pace_tolerance_sec": 5,
    })
    result = json.loads(update_running_workout("99999", spec))
    assert result["updated"] is True
    assert result["workoutId"] == 99999
    garmin_mock.client.put.assert_called_once()
    garmin_mock.upload_workout.assert_not_called()


def test_update_invalid_json(garmin_mock):
    assert "error" in json.loads(update_running_workout("99999", "bad json"))
