import json

import auth
from app import mcp
from garminconnect.workout import (
    ExecutableStep,
    SwimmingWorkout,
    WorkoutSegment,
    create_repeat_group,
)
from utils import serialize


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SPORT_TYPE      = {"sportTypeId": 4, "sportTypeKey": "swimming", "displayOrder": 3}
_POOL_LENGTH_UNIT = {"unitId": 1, "unitKey": "meter", "factor": 100.0}

_STROKE_MAP = {
    "any":         {"strokeTypeId": 1, "strokeTypeKey": "any_stroke",   "displayOrder": 1},
    "backstroke":  {"strokeTypeId": 2, "strokeTypeKey": "backstroke",   "displayOrder": 2},
    "breaststroke":{"strokeTypeId": 3, "strokeTypeKey": "breaststroke", "displayOrder": 3},
    "butterfly":   {"strokeTypeId": 4, "strokeTypeKey": "butterfly",    "displayOrder": 4},
    "drill":       {"strokeTypeId": 5, "strokeTypeKey": "drill",        "displayOrder": 5},
    "free":        {"strokeTypeId": 6, "strokeTypeKey": "free",         "displayOrder": 6},
}

_NO_STROKE    = {"strokeTypeId": 0, "strokeTypeKey": None, "displayOrder": 0}
_NO_EQUIPMENT = {"equipmentTypeId": 0, "equipmentTypeKey": None, "displayOrder": 0}
_NO_TARGET    = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1}

_STEP_TYPE_MAP = {
    "warmup":   {"stepTypeId": 1, "stepTypeKey": "warmup",   "displayOrder": 1},
    "cooldown": {"stepTypeId": 2, "stepTypeKey": "cooldown",  "displayOrder": 2},
    "rest":     {"stepTypeId": 5, "stepTypeKey": "rest",      "displayOrder": 5},
    "main":     {"stepTypeId": 8, "stepTypeKey": "main",      "displayOrder": 8},
    "drill":    {"stepTypeId": 8, "stepTypeKey": "main",      "displayOrder": 8},
}

_DISTANCE_CONDITION = {
    "conditionTypeId": 3, "conditionTypeKey": "distance",
    "displayOrder": 3, "displayable": True,
}
_LAP_BUTTON_CONDITION = {
    "conditionTypeId": 1, "conditionTypeKey": "lap.button",
    "displayOrder": 1, "displayable": True,
}
_FIXED_REST_CONDITION = {
    "conditionTypeId": 8, "conditionTypeKey": "fixed.rest",
    "displayOrder": 8, "displayable": True,
}


# ---------------------------------------------------------------------------
# Step builders
# ---------------------------------------------------------------------------

def _distance_step(step_type: str, distance_m: float, stroke: str, order: int) -> ExecutableStep:
    return ExecutableStep(
        stepOrder=order,
        stepType=_STEP_TYPE_MAP.get(step_type, _STEP_TYPE_MAP["main"]),
        endCondition=_DISTANCE_CONDITION,
        endConditionValue=float(distance_m),
        preferredEndConditionUnit=_POOL_LENGTH_UNIT,
        targetType=_NO_TARGET,
        strokeType=_STROKE_MAP.get(stroke, _NO_STROKE),
        equipmentType=_NO_EQUIPMENT,
    )


def _rest_step(order: int, rest_seconds: float | None = None) -> ExecutableStep:
    """Lap-button rest (between blocks) or fixed-rest (within repeat groups)."""
    if rest_seconds:
        return ExecutableStep(
            stepOrder=order,
            stepType=_STEP_TYPE_MAP["rest"],
            endCondition=_FIXED_REST_CONDITION,
            endConditionValue=float(rest_seconds),
            targetType=_NO_TARGET,
            strokeType=_NO_STROKE,
            equipmentType=_NO_EQUIPMENT,
        )
    return ExecutableStep(
        stepOrder=order,
        stepType=_STEP_TYPE_MAP["rest"],
        endCondition=_LAP_BUTTON_CONDITION,
        endConditionValue=None,
        targetType=_NO_TARGET,
        strokeType=_NO_STROKE,
        equipmentType=_NO_EQUIPMENT,
    )


def _step_distance(spec: dict) -> float:
    """Total distance in meters for a step spec, expanding nested repeats."""
    if spec.get("type") == "repeat":
        inner = sum(
            float(s.get("distance", 0))
            for s in spec.get("steps", [])
            if s.get("type") != "rest"
        )
        return inner * int(spec.get("repeat", 1))
    if spec.get("type") == "rest":
        return 0.0
    return float(spec.get("distance", 0))


def _build_swim_steps(main_set: list[dict], order_start: int) -> list:
    steps = []
    order = order_start
    for spec in main_set:
        stype = spec.get("type", "main")
        if stype == "repeat":
            inner  = []
            iorder = 1
            for inner_spec in spec.get("steps", []):
                itype = inner_spec.get("type", "main")
                if itype == "rest":
                    inner.append(_rest_step(iorder, inner_spec.get("rest_seconds")))
                else:
                    inner.append(_distance_step(
                        itype,
                        float(inner_spec.get("distance", 0)),
                        inner_spec.get("stroke", "free"),
                        iorder,
                    ))
                iorder += 1
            steps.append(create_repeat_group(int(spec.get("repeat", 1)), inner, order))
        elif stype == "rest":
            steps.append(_rest_step(order, spec.get("rest_seconds")))
        else:
            steps.append(_distance_step(
                stype,
                float(spec.get("distance", 0)),
                spec.get("stroke", "free"),
                order,
            ))
        order += 1
    return steps


# ---------------------------------------------------------------------------
# MCP tool
# ---------------------------------------------------------------------------

@mcp.tool()
def create_swimming_workout(workout_json: str) -> str:
    """
    Create a structured pool swimming workout in Garmin Connect.

    workout_json schema:
    {
      "name": "Natação S1 — Drills + 8x100",
      "description": "optional",
      "pool_length": 25,
      "main_set": [
        {"type": "warmup",   "distance": 400, "stroke": "free"},
        {"type": "rest"},
        {
          "type": "repeat", "repeat": 8,
          "steps": [
            {"type": "main", "distance": 100, "stroke": "free"},
            {"type": "rest", "rest_seconds": 15}
          ]
        },
        {"type": "rest"},
        {"type": "cooldown", "distance": 200, "stroke": "any"}
      ]
    }

    Step types:
    - warmup   : opening warmup, distance-based
    - main     : main interval, distance-based
    - drill    : drill step (alias of main, use stroke="drill")
    - cooldown : closing cooldown, distance-based
    - rest     : lap-button rest between blocks (no rest_seconds),
                 or fixed rest inside repeat groups (rest_seconds in seconds)
    - repeat   : repeat group with nested steps

    Stroke options: free, backstroke, breaststroke, butterfly, drill, any
    Pool length  : 25 or 50 (meters, default 25)

    Returns the created workout id and total distance in meters.
    """
    try:
        spec = json.loads(workout_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    name        = spec.get("name", "Swimming Workout")
    description = spec.get("description")
    pool_length = float(spec.get("pool_length", 25))
    main_set    = spec.get("main_set", [])

    all_steps = _build_swim_steps(main_set, order_start=1)
    total_m   = sum(_step_distance(s) for s in main_set)

    workout = SwimmingWorkout(
        workoutName=name,
        description=description,
        estimatedDurationInSecs=0,
        workoutSegments=[
            WorkoutSegment(
                segmentOrder=1,
                sportType=_SPORT_TYPE,
                workoutSteps=all_steps,
            )
        ],
    )
    workout.model_extra["poolLength"]               = pool_length
    workout.model_extra["poolLengthUnit"]           = _POOL_LENGTH_UNIT
    workout.model_extra["estimatedDistanceInMeters"] = total_m

    result     = auth.get_client().upload_swimming_workout(workout)
    workout_id = result.get("workoutId") or result.get("workout", {}).get("workoutId")
    return serialize({"workoutId": workout_id, "name": name, "estimatedDistanceMeters": total_m})
