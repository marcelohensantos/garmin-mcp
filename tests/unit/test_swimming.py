import json

from tools.swimming import create_swimming_workout

_BASIC_WORKOUT = json.dumps({
    "name": "Natação S1 — Drills + 8x100",
    "pool_length": 25,
    "main_set": [
        {"type": "warmup",   "distance": 400, "stroke": "free"},
        {"type": "rest"},
        {
            "type": "repeat", "repeat": 8,
            "steps": [
                {"type": "main", "distance": 100, "stroke": "free"},
                {"type": "rest", "rest_seconds": 15},
            ],
        },
        {"type": "rest"},
        {"type": "cooldown", "distance": 200, "stroke": "any"},
    ],
})


def test_create_swimming_workout_returns_id(garmin_mock):
    result = json.loads(create_swimming_workout(_BASIC_WORKOUT))
    assert result["workoutId"] == 99999
    assert result["name"] == "Natação S1 — Drills + 8x100"
    garmin_mock.upload_workout.assert_called_once()


def test_total_distance_is_correct(garmin_mock):
    # 400 warmup + 8×100 main + 200 cooldown = 1400m (rests have no distance)
    result = json.loads(create_swimming_workout(_BASIC_WORKOUT))
    assert result["estimatedDistanceMeters"] == 1400.0


def test_invalid_json_returns_error(garmin_mock):
    assert "error" in json.loads(create_swimming_workout("not json"))


def test_step_structure(garmin_mock):
    create_swimming_workout(_BASIC_WORKOUT)
    payload = garmin_mock.upload_workout.call_args[0][0]
    steps   = payload["workoutSegments"][0]["workoutSteps"]

    # warmup, lap-rest, repeat-group, lap-rest, cooldown
    assert len(steps) == 5
    assert steps[0]["stepType"]["stepTypeKey"] == "warmup"
    assert steps[0]["endConditionValue"] == 400.0
    assert steps[1]["endCondition"]["conditionTypeKey"] == "lap.button"
    assert steps[2]["numberOfIterations"] == 8
    assert steps[3]["endCondition"]["conditionTypeKey"] == "lap.button"
    assert steps[4]["stepType"]["stepTypeKey"] == "cooldown"
    assert steps[4]["endConditionValue"] == 200.0


def test_repeat_group_inner_steps(garmin_mock):
    create_swimming_workout(_BASIC_WORKOUT)
    payload = garmin_mock.upload_workout.call_args[0][0]
    inner   = payload["workoutSegments"][0]["workoutSteps"][2]["workoutSteps"]

    assert len(inner) == 2
    assert inner[0]["stepType"]["stepTypeKey"] == "main"
    assert inner[0]["endConditionValue"] == 100.0
    assert inner[1]["endCondition"]["conditionTypeKey"] == "fixed.rest"
    assert inner[1]["endConditionValue"] == 15.0


def test_pool_length_is_set(garmin_mock):
    create_swimming_workout(_BASIC_WORKOUT)
    payload = garmin_mock.upload_workout.call_args[0][0]
    assert payload["poolLength"] == 25.0
    assert payload["poolLengthUnit"]["unitKey"] == "meter"


def test_sport_type_is_swimming(garmin_mock):
    create_swimming_workout(_BASIC_WORKOUT)
    payload = garmin_mock.upload_workout.call_args[0][0]
    assert payload["sportType"]["sportTypeId"] == 4
    assert payload["sportType"]["sportTypeKey"] == "swimming"
