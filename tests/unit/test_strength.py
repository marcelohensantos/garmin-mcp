import json

from tools.strength import create_strength_workout

_PUSH_WORKOUT = json.dumps({
    "name": "Push",
    "description": "Chest, shoulders, triceps",
    "exercises": [
        {"name": "BARBELL_BENCH_PRESS",     "category": "BENCH_PRESS",
         "sets": 3, "reps": 12, "weight_kg": 60.0, "rest_seconds": 90},
        {"name": "DUMBBELL_SHOULDER_PRESS", "category": "SHOULDER_PRESS",
         "sets": 3, "reps": 12, "weight_kg": 16.0, "rest_seconds": 60},
        {"name": "PUSH_UP",                 "category": "PUSH_UP",
         "sets": 3, "reps": 15, "weight_kg": -1.0, "rest_seconds": 60},
    ],
})


def test_create_strength_workout_returns_id(garmin_mock):
    result = json.loads(create_strength_workout(_PUSH_WORKOUT))
    assert result["workoutId"] == 99999
    assert result["name"] == "Push"
    garmin_mock.upload_workout.assert_called_once()


def test_invalid_json_returns_error(garmin_mock):
    result = json.loads(create_strength_workout("not json"))
    assert "error" in result


def test_sport_type_is_strength(garmin_mock):
    create_strength_workout(_PUSH_WORKOUT)
    payload = garmin_mock.upload_workout.call_args[0][0]
    assert payload["sportType"]["sportTypeId"] == 5
    assert payload["sportType"]["sportTypeKey"] == "strength_training"


def test_step_structure(garmin_mock):
    create_strength_workout(_PUSH_WORKOUT)
    payload = garmin_mock.upload_workout.call_args[0][0]
    steps   = payload["workoutSegments"][0]["workoutSteps"]

    # warmup + 3 repeat groups (one per exercise)
    assert len(steps) == 4
    assert steps[0]["stepType"]["stepTypeKey"] == "warmup"
    assert steps[0]["endCondition"]["conditionTypeKey"] == "lap.button"


def test_repeat_group_structure(garmin_mock):
    create_strength_workout(_PUSH_WORKOUT)
    payload      = garmin_mock.upload_workout.call_args[0][0]
    repeat_group = payload["workoutSegments"][0]["workoutSteps"][1]

    assert repeat_group["type"] == "RepeatGroupDTO"
    assert repeat_group["numberOfIterations"] == 3

    inner = repeat_group["workoutSteps"]
    assert len(inner) == 2
    assert inner[0]["stepType"]["stepTypeKey"] == "interval"
    assert inner[0]["endCondition"]["conditionTypeKey"] == "reps"
    assert inner[0]["endConditionValue"] == 12.0
    assert inner[1]["stepType"]["stepTypeKey"] == "rest"
    assert inner[1]["endCondition"]["conditionTypeKey"] == "time"
    assert inner[1]["endConditionValue"] == 90.0


def test_exercise_fields(garmin_mock):
    create_strength_workout(_PUSH_WORKOUT)
    payload       = garmin_mock.upload_workout.call_args[0][0]
    exercise_step = payload["workoutSegments"][0]["workoutSteps"][1]["workoutSteps"][0]

    assert exercise_step["category"]     == "BENCH_PRESS"
    assert exercise_step["exerciseName"] == "BARBELL_BENCH_PRESS"
    assert exercise_step["weightValue"]  == 60.0
    assert exercise_step["weightUnit"]["unitKey"] == "kilogram"


def test_bodyweight_exercise(garmin_mock):
    create_strength_workout(_PUSH_WORKOUT)
    payload       = garmin_mock.upload_workout.call_args[0][0]
    pushup_group  = payload["workoutSegments"][0]["workoutSteps"][3]
    exercise_step = pushup_group["workoutSteps"][0]

    assert exercise_step["weightValue"] == -1.0
