import json

import auth
from app import mcp
from garminconnect.workout import BaseWorkout, ExecutableStep, WorkoutSegment, create_repeat_group
from utils import serialize


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SPORT_TYPE = {"sportTypeId": 5, "sportTypeKey": "strength_training", "displayOrder": 12}

_STEP_TYPE_INTERVAL = {"stepTypeId": 3, "stepTypeKey": "interval",  "displayOrder": 3}
_STEP_TYPE_REST     = {"stepTypeId": 5, "stepTypeKey": "rest",       "displayOrder": 5}
_STEP_TYPE_WARMUP   = {"stepTypeId": 1, "stepTypeKey": "warmup",     "displayOrder": 1}

_REPS_CONDITION = {
    "conditionTypeId": 10, "conditionTypeKey": "reps",
    "displayOrder": 10, "displayable": True,
}
_TIME_CONDITION = {
    "conditionTypeId": 2, "conditionTypeKey": "time",
    "displayOrder": 2, "displayable": True,
}
_LAP_BUTTON_CONDITION = {
    "conditionTypeId": 1, "conditionTypeKey": "lap.button",
    "displayOrder": 1, "displayable": True,
}

_NO_TARGET = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1}
_WEIGHT_UNIT_KG = {"unitId": 8, "unitKey": "kilogram", "factor": 1000.0}


# ---------------------------------------------------------------------------
# Step builders
# ---------------------------------------------------------------------------

def _warmup_step(order: int) -> ExecutableStep:
    return ExecutableStep(
        stepOrder=order,
        stepType=_STEP_TYPE_WARMUP,
        endCondition=_LAP_BUTTON_CONDITION,
        endConditionValue=None,
        targetType=_NO_TARGET,
    )


def _exercise_step(reps: int, category: str, exercise_name: str, weight_kg: float, order: int) -> ExecutableStep:
    step = ExecutableStep(
        stepOrder=order,
        stepType=_STEP_TYPE_INTERVAL,
        endCondition=_REPS_CONDITION,
        endConditionValue=float(reps),
        targetType=_NO_TARGET,
    )
    step.model_extra["category"]      = category.upper()
    step.model_extra["exerciseName"]  = exercise_name.upper()
    step.model_extra["weightValue"]   = float(weight_kg)
    step.model_extra["weightUnit"]    = _WEIGHT_UNIT_KG
    return step


def _rest_step(rest_seconds: int, order: int) -> ExecutableStep:
    return ExecutableStep(
        stepOrder=order,
        stepType=_STEP_TYPE_REST,
        endCondition=_TIME_CONDITION,
        endConditionValue=float(rest_seconds),
        targetType=_NO_TARGET,
    )


def _build_strength_steps(exercises: list[dict]) -> list:
    """Build one RepeatGroup per exercise (sets × [interval + rest])."""
    steps = []
    order = 1

    steps.append(_warmup_step(order))
    order += 1

    for ex in exercises:
        name         = ex.get("name", "UNKNOWN")
        category     = ex.get("category", "OTHER")
        sets         = int(ex.get("sets", 3))
        reps         = int(ex.get("reps", 10))
        weight_kg    = float(ex.get("weight_kg", -1.0))
        rest_seconds = int(ex.get("rest_seconds", 60))

        inner = [
            _exercise_step(reps, category, name, weight_kg, 1),
            _rest_step(rest_seconds, 2),
        ]
        steps.append(create_repeat_group(sets, inner, order))
        order += 1

    return steps


# ---------------------------------------------------------------------------
# MCP tool
# ---------------------------------------------------------------------------

@mcp.tool()
def create_strength_workout(workout_json: str) -> str:
    """
    Create a structured strength training workout in Garmin Connect.

    workout_json schema:
    {
      "name": "Força A — Upper Focus",
      "description": "optional",
      "exercises": [
        {
          "name": "LAT_PULLDOWN",
          "category": "PULL_UP",
          "sets": 4,
          "reps": 12,
          "weight_kg": 35.0,
          "rest_seconds": 75
        },
        {
          "name": "DUMBBELL_SHOULDER_PRESS",
          "category": "SHOULDER_PRESS",
          "sets": 3,
          "reps": 12,
          "weight_kg": 10.0,
          "rest_seconds": 60
        }
      ]
    }

    Fields:
    - name        : Garmin exercise name constant (e.g. LAT_PULLDOWN, SEATED_CABLE_ROW,
                    ROMANIAN_DEADLIFT, BARBELL_BACK_SQUAT, HIP_THRUST, MACHINE_CHEST_PRESS,
                    DUMBBELL_SHOULDER_PRESS, STANDING_CALF_RAISE, DEAD_BUG, PLANK).
                    Use empty string "" when no specific Garmin name applies.
    - category    : Garmin exercise category constant. VALID values (confirmed against API):
                    PULL_UP, ROW, SHOULDER_PRESS, LATERAL_RAISE, TRICEPS_EXTENSION, CURL,
                    BENCH_PRESS, SQUAT, DEADLIFT, LUNGE, HIP_RAISE, HIP_STABILITY,
                    LEG_CURL, CALF_RAISE, FLYE, PUSH_UP, PLANK, CORE.
                    INVALID (cause 400 error): CHEST, BACK, SHOULDERS.
    - sets        : number of sets (becomes RepeatGroup iterations)
    - reps        : reps per set
    - weight_kg   : weight in kg; use -1.0 for bodyweight exercises
    - rest_seconds: rest between sets in seconds (default 60)

    Each exercise becomes one RepeatGroup of sets × [interval(reps) + rest(time)].
    The workout begins with a lap-button warmup step.

    Returns the created workout id.
    """
    try:
        spec = json.loads(workout_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    name        = spec.get("name", "Strength Workout")
    description = spec.get("description")
    exercises   = spec.get("exercises", [])

    all_steps = _build_strength_steps(exercises)

    workout = BaseWorkout(
        workoutName=name,
        description=description,
        sportType=_SPORT_TYPE,
        estimatedDurationInSecs=0,
        workoutSegments=[
            WorkoutSegment(
                segmentOrder=1,
                sportType=_SPORT_TYPE,
                workoutSteps=all_steps,
            )
        ],
    )

    result     = auth.get_client().upload_workout(workout.to_dict())
    workout_id = result.get("workoutId") or result.get("workout", {}).get("workoutId")
    return serialize({"workoutId": workout_id, "name": name})
