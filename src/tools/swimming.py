"""Swimming workout creation for Garmin Connect."""
import json

from app import mcp
from tools.builder import WorkoutBuilder, repeat_group
from utils import serialize

_SPORT     = {"sportTypeId": 4, "sportTypeKey": "swimming",  "displayOrder": 3}
_POOL_UNIT = {"unitId": 1, "unitKey": "meter", "factor": 100.0}
_NO_TARGET = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1}
_NO_STROKE = {"strokeTypeId": 0, "strokeTypeKey": None, "displayOrder": 0}
_NO_EQUIP  = {"equipmentTypeId": 0, "equipmentTypeKey": None, "displayOrder": 0}

_COND_DIST       = {"conditionTypeId": 3, "conditionTypeKey": "distance",   "displayOrder": 3, "displayable": True}  # noqa: E501
_COND_LAP        = {"conditionTypeId": 1, "conditionTypeKey": "lap.button", "displayOrder": 1, "displayable": True}  # noqa: E501
_COND_FIXED_REST = {"conditionTypeId": 8, "conditionTypeKey": "fixed.rest", "displayOrder": 8, "displayable": True}  # noqa: E501

_STEP_TYPES = {
    "warmup":   {"stepTypeId": 1, "stepTypeKey": "warmup",   "displayOrder": 1},
    "cooldown": {"stepTypeId": 2, "stepTypeKey": "cooldown",  "displayOrder": 2},
    "rest":     {"stepTypeId": 5, "stepTypeKey": "rest",      "displayOrder": 5},
    "main":     {"stepTypeId": 8, "stepTypeKey": "main",      "displayOrder": 8},
    "drill":    {"stepTypeId": 8, "stepTypeKey": "main",      "displayOrder": 8},
}
_STROKES = {
    "any":          {"strokeTypeId": 1, "strokeTypeKey": "any_stroke",   "displayOrder": 1},
    "backstroke":   {"strokeTypeId": 2, "strokeTypeKey": "backstroke",   "displayOrder": 2},
    "breaststroke": {"strokeTypeId": 3, "strokeTypeKey": "breaststroke", "displayOrder": 3},
    "butterfly":    {"strokeTypeId": 4, "strokeTypeKey": "butterfly",    "displayOrder": 4},
    "drill":        {"strokeTypeId": 5, "strokeTypeKey": "drill",        "displayOrder": 5},
    "free":         {"strokeTypeId": 6, "strokeTypeKey": "free",         "displayOrder": 6},
}


# ---------------------------------------------------------------------------
# Step builders
# ---------------------------------------------------------------------------

def _swim_step(step_type: str, order: int, distance_m: float, stroke: str) -> dict:
    return {
        "type":                      "ExecutableStepDTO",
        "stepOrder":                 order,
        "stepType":                  _STEP_TYPES.get(step_type, _STEP_TYPES["main"]),
        "endCondition":              _COND_DIST,
        "endConditionValue":         float(distance_m),
        "preferredEndConditionUnit": _POOL_UNIT,
        "targetType":                _NO_TARGET,
        "strokeType":                _STROKES.get(stroke, _NO_STROKE),
        "equipmentType":             _NO_EQUIP,
    }


def _rest_step(order: int, rest_seconds: float = None) -> dict:
    return {
        "type":              "ExecutableStepDTO",
        "stepOrder":         order,
        "stepType":          _STEP_TYPES["rest"],
        "endCondition":      _COND_FIXED_REST if rest_seconds else _COND_LAP,
        "endConditionValue": float(rest_seconds) if rest_seconds else None,
        "targetType":        _NO_TARGET,
        "strokeType":        _NO_STROKE,
        "equipmentType":     _NO_EQUIP,
    }


def _step_distance(spec: dict) -> float:
    if spec.get("type") == "repeat":
        inner = sum(float(s.get("distance", 0))
                    for s in spec.get("steps", [])
                    if s.get("type") != "rest")
        return inner * int(spec.get("repeat", 1))
    return 0.0 if spec.get("type") == "rest" else float(spec.get("distance", 0))


def _build_steps(main_set: list[dict], order_start: int) -> list[dict]:
    steps = []
    order = order_start
    for spec in main_set:
        stype = spec.get("type", "main")
        if stype == "repeat":
            inner = []
            for i, s in enumerate(spec.get("steps", []), start=1):
                if s.get("type") == "rest":
                    inner.append(_rest_step(i, s.get("rest_seconds")))
                else:
                    inner.append(_swim_step(s.get("type", "main"), i,
                                            float(s.get("distance", 0)),
                                            s.get("stroke", "free")))
            steps.append(repeat_group(order, int(spec.get("repeat", 1)), inner,
                                      skip_last_rest=False))
        elif stype == "rest":
            steps.append(_rest_step(order, spec.get("rest_seconds")))
        else:
            steps.append(_swim_step(stype, order, float(spec.get("distance", 0)),
                                    spec.get("stroke", "free")))
        order += 1
    return steps


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class SwimmingBuilder(WorkoutBuilder):
    def build_payload(self, spec: dict) -> dict:
        name        = spec.get("name", "Swimming Workout")
        description = spec.get("description")
        pool_length = float(spec.get("pool_length", 25))
        main_set    = spec.get("main_set", [])

        steps   = _build_steps(main_set, order_start=1)
        total_m = sum(_step_distance(s) for s in main_set)

        return {
            "workoutName":               name,
            "description":               description,
            "sportType":                 _SPORT,
            "poolLength":                pool_length,
            "poolLengthUnit":            _POOL_UNIT,
            "estimatedDistanceInMeters": total_m,
            "workoutSegments": [{
                "segmentOrder":  1,
                "sportType":     _SPORT,
                "poolLength":    pool_length,
                "poolLengthUnit": _POOL_UNIT,
                "workoutSteps":  steps,
            }],
        }


_builder = SwimmingBuilder()


@mcp.tool()
def create_swimming_workout(workout_json: str) -> str:
    """
    Create a structured pool swimming workout in Garmin Connect.

    {
      "name": "Natação S1 — Drills + 8×100",
      "description": "optional",
      "pool_length": 25,
      "main_set": [
        {"type": "warmup",   "distance": 400, "stroke": "free"},
        {"type": "rest"},
        {
          "type": "repeat", "repeat": 8,
          "steps": [
            {"type": "main",  "distance": 100, "stroke": "free"},
            {"type": "rest",  "rest_seconds": 15}
          ]
        },
        {"type": "rest"},
        {"type": "cooldown", "distance": 200, "stroke": "any"}
      ]
    }

    Step types: warmup, main, drill, cooldown, rest, repeat.
    Strokes: free, backstroke, breaststroke, butterfly, drill, any.
    rest without rest_seconds → lap-button; with rest_seconds → fixed rest.
    Pool length: 25 or 50 m (default 25).
    Returns the created workout id and total distance in meters.
    """
    try:
        spec = json.loads(workout_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})
    result = _builder.create(spec)
    result["estimatedDistanceMeters"] = sum(_step_distance(s)
                                            for s in spec.get("main_set", []))
    return serialize(result)
