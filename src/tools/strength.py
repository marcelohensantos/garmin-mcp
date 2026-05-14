"""Strength workout creation for Garmin Connect."""
import json

from app import mcp
from tools.builder import WorkoutBuilder, repeat_group
from utils import serialize

_SPORT      = {"sportTypeId": 5, "sportTypeKey": "strength_training", "displayOrder": 12}
_NO_TARGET  = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1}
_WEIGHT_KG  = {"unitId": 8, "unitKey": "kilogram", "factor": 1000.0}

_COND_REPS  = {"conditionTypeId": 10, "conditionTypeKey": "reps",       "displayOrder": 10, "displayable": True}  # noqa: E501
_COND_TIME  = {"conditionTypeId": 2,  "conditionTypeKey": "time",       "displayOrder": 2,  "displayable": True}  # noqa: E501
_COND_LAP   = {"conditionTypeId": 1,  "conditionTypeKey": "lap.button", "displayOrder": 1,  "displayable": True}  # noqa: E501

_STEP_INTERVAL = {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3}
_STEP_REST     = {"stepTypeId": 5, "stepTypeKey": "rest",     "displayOrder": 5}
_STEP_WARMUP   = {"stepTypeId": 1, "stepTypeKey": "warmup",   "displayOrder": 1}


# ---------------------------------------------------------------------------
# Step builders
# ---------------------------------------------------------------------------

def _warmup_step(order: int) -> dict:
    return {
        "type":              "ExecutableStepDTO",
        "stepOrder":         order,
        "stepType":          _STEP_WARMUP,
        "endCondition":      _COND_LAP,
        "endConditionValue": None,
        "targetType":        _NO_TARGET,
    }


def _exercise_step(order: int, reps: int, category: str,
                   name: str, weight_kg: float) -> dict:
    return {
        "type":              "ExecutableStepDTO",
        "stepOrder":         order,
        "stepType":          _STEP_INTERVAL,
        "endCondition":      _COND_REPS,
        "endConditionValue": float(reps),
        "targetType":        _NO_TARGET,
        "category":          category.upper(),
        "exerciseName":      name.upper(),
        "weightValue":       float(weight_kg),
        "weightUnit":        _WEIGHT_KG,
    }


def _rest_step(order: int, seconds: int) -> dict:
    return {
        "type":              "ExecutableStepDTO",
        "stepOrder":         order,
        "stepType":          _STEP_REST,
        "endCondition":      _COND_TIME,
        "endConditionValue": float(seconds),
        "targetType":        _NO_TARGET,
    }


def _build_steps(exercises: list[dict]) -> list[dict]:
    steps = [_warmup_step(1)]
    for i, ex in enumerate(exercises, start=2):
        inner = [
            _exercise_step(1, int(ex.get("reps", 10)), ex.get("category", "OTHER"),
                           ex.get("name", ""), float(ex.get("weight_kg", -1.0))),
            _rest_step(2, int(ex.get("rest_seconds", 60))),
        ]
        steps.append(repeat_group(i, int(ex.get("sets", 3)), inner))
    return steps


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class StrengthBuilder(WorkoutBuilder):
    def build_payload(self, spec: dict) -> dict:
        steps = _build_steps(spec.get("exercises", []))
        return {
            "workoutName":     spec.get("name", "Strength Workout"),
            "description":     spec.get("description"),
            "sportType":       _SPORT,
            "workoutSegments": [{
                "segmentOrder": 1,
                "sportType":    _SPORT,
                "workoutSteps": steps,
            }],
        }


_builder = StrengthBuilder()


@mcp.tool()
def create_strength_workout(workout_json: str) -> str:
    """
    Create a structured strength training workout in Garmin Connect.

    {
      "name": "Força A — Upper Focus",
      "description": "optional",
      "exercises": [
        {
          "name": "LAT_PULLDOWN",
          "category": "PULL_UP",
          "sets": 4, "reps": 12, "weight_kg": 35.0, "rest_seconds": 75
        }
      ]
    }

    category valid values: PULL_UP, ROW, SHOULDER_PRESS, LATERAL_RAISE,
    TRICEPS_EXTENSION, CURL, BENCH_PRESS, SQUAT, DEADLIFT, LUNGE, HIP_RAISE,
    HIP_STABILITY, LEG_CURL, CALF_RAISE, FLYE, PUSH_UP, PLANK, CORE.
    Use weight_kg: -1.0 for bodyweight. Each exercise → one RepeatGroup (sets × [interval + rest]).
    The workout begins with a lap-button warmup step.
    """
    try:
        spec = json.loads(workout_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})
    return serialize(_builder.create(spec))
