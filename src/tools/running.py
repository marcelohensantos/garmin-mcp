"""Running workout creation for Garmin Connect."""
import json

from app import mcp
from tools.builder import WorkoutBuilder, repeat_group
from utils import serialize

_SPORT      = {"sportTypeId": 1, "sportTypeKey": "running",   "displayOrder": 1}
_NO_TARGET  = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target",  "displayOrder": 1}
_PACE_ZONE  = {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone",  "displayOrder": 6}
_COND_TIME  = {"conditionTypeId": 2, "conditionTypeKey": "time",       "displayOrder": 2, "displayable": True}
_COND_DIST  = {"conditionTypeId": 3, "conditionTypeKey": "distance",   "displayOrder": 3, "displayable": True}
_COND_LAP   = {"conditionTypeId": 1, "conditionTypeKey": "lap.button", "displayOrder": 1, "displayable": True}
_KM         = {"unitId": 2, "unitKey": "kilometer", "factor": 100000.0}
_STROKE     = {"strokeTypeId": 0, "strokeTypeKey": None, "displayOrder": 0}
_EQUIP      = {"equipmentTypeId": 0, "equipmentTypeKey": None, "displayOrder": 0}


# ---------------------------------------------------------------------------
# Pace helpers
# ---------------------------------------------------------------------------

def _pace_target(pace: str, tolerance_sec: int) -> dict:
    """M:SS/km → pace.zone dict (m/s, ±tolerance). fast > slow in m/s."""
    m, s      = pace.strip().split(":")
    total_sec = int(m) * 60 + int(s)
    return {
        "targetType":     _PACE_ZONE,
        "targetValueOne": round(1000 / (total_sec - tolerance_sec), 7),
        "targetValueTwo": round(1000 / (total_sec + tolerance_sec), 7),
    }


def _pace_range(fast: str, slow: str) -> dict:
    """Explicit fast/slow bounds → pace.zone dict (m/s, no tolerance)."""
    def to_ms(p):
        m, s = p.strip().split(":")
        return round(1000 / (int(m) * 60 + int(s)), 7)
    return {"targetType": _PACE_ZONE, "targetValueOne": to_ms(fast), "targetValueTwo": to_ms(slow)}


# ---------------------------------------------------------------------------
# Step builders
# ---------------------------------------------------------------------------

def _step(type_id: int, type_key: str, order: int, end_cond: dict, end_value,
          target: dict = None, val_one=None, val_two=None,
          child_id: int = None, pref_unit: dict = None) -> dict:
    s = {
        "type":              "ExecutableStepDTO",
        "stepOrder":         order,
        "stepType":          {"stepTypeId": type_id, "stepTypeKey": type_key, "displayOrder": type_id},
        "endCondition":      end_cond,
        "endConditionValue": end_value,
        "targetType":        target or _NO_TARGET,
        "targetValueOne":    val_one,
        "targetValueTwo":    val_two,
        "strokeType":        _STROKE,
        "equipmentType":     _EQUIP,
    }
    if child_id is not None:
        s["childStepId"] = child_id
    if pref_unit:
        s["preferredEndConditionUnit"] = pref_unit
    return s


def _distance_step(type_id: int, type_key: str, order: int, distance_m: float,
                   pace_fast: str = None, pace_slow: str = None) -> dict:
    tgt = _pace_range(pace_fast, pace_slow) if pace_fast and pace_slow else {}
    return _step(type_id, type_key, order, _COND_DIST, distance_m,
                 target=tgt.get("targetType"), val_one=tgt.get("targetValueOne"),
                 val_two=tgt.get("targetValueTwo"), pref_unit=_KM)


def _time_interval(order: int, duration_sec: float, child_id: int = None,
                   pace: str = None, tolerance_sec: int = 10) -> dict:
    tgt = _pace_target(pace, tolerance_sec) if pace else {}
    return _step(3, "interval", order, _COND_TIME, duration_sec,
                 target=tgt.get("targetType"), val_one=tgt.get("targetValueOne"),
                 val_two=tgt.get("targetValueTwo"), child_id=child_id)


def _time_recovery(order: int, duration_sec: float, child_id: int = None) -> dict:
    return _step(4, "recovery", order, _COND_TIME, duration_sec, child_id=child_id)


def _lap_cooldown(order: int) -> dict:
    return _step(2, "cooldown", order, _COND_LAP, None)


# ---------------------------------------------------------------------------
# Main-set builder
# ---------------------------------------------------------------------------

def _build_main(main_set: list[dict], tolerance_sec: int, order_start: int) -> list[dict]:
    steps = []
    order = order_start
    for spec in main_set:
        stype = spec.get("type")
        if stype == "repeat":
            inner_order = order + 1
            inner = []
            for s in spec.get("steps", []):
                dur = float(s.get("minutes", 0)) * 60 + float(s.get("seconds", 0))
                if s.get("type") == "interval":
                    inner.append(_time_interval(inner_order, dur, 1, s.get("pace"), tolerance_sec))
                else:
                    inner.append(_time_recovery(inner_order, dur, 1))
                inner_order += 1
            steps.append(repeat_group(order, int(spec.get("repeat", 1)), inner))
        elif stype == "interval":
            dur = float(spec.get("minutes", 0)) * 60 + float(spec.get("seconds", 0))
            steps.append(_time_interval(order, dur, pace=spec.get("pace"), tolerance_sec=tolerance_sec))
        elif stype == "recovery":
            dur = float(spec.get("minutes", 0)) * 60 + float(spec.get("seconds", 0))
            steps.append(_time_recovery(order, dur))
        order += 1
    return steps


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class RunningBuilder(WorkoutBuilder):
    def build_payload(self, spec: dict) -> dict:
        tolerance     = int(spec.get("pace_tolerance_sec", 10))
        main_set      = spec.get("main_set", [])
        repeat        = int(spec.get("repeat", 1))
        warmup_km     = spec.get("warmup_km")
        cooldown_km   = spec.get("cooldown_km")
        main_km       = spec.get("main_km")
        warmup_pace   = spec.get("warmup_pace")
        cooldown_pace = spec.get("cooldown_pace")
        main_pace     = spec.get("main_pace")

        steps = []
        order = 1

        if warmup_km is not None or cooldown_km is not None or main_km is not None:
            if warmup_km:
                steps.append(_distance_step(1, "warmup", order, float(warmup_km) * 1000,
                                            *(warmup_pace or [None, None])))
                order += 1
            if main_km:
                steps.append(_distance_step(3, "interval", order, float(main_km) * 1000,
                                            *(main_pace or [None, None])))
                order += 1
            elif main_set:
                raw = _build_main(main_set, tolerance, order)
                steps.extend(raw)
                order += len(raw)
            if cooldown_km:
                steps.append(_distance_step(2, "cooldown", order, float(cooldown_km) * 1000,
                                            *(cooldown_pace or [None, None])))
                order += 1
        else:
            warmup_min   = float(spec.get("warmup_minutes", 10))
            cooldown_min = float(spec.get("cooldown_minutes", 10))
            simple = (repeat == 1 and len(main_set) == 1
                      and main_set[0].get("type") != "repeat"
                      and not main_set[0].get("pace"))
            if simple:
                s         = main_set[0]
                total_sec = int((warmup_min + float(s.get("minutes", 0)) + cooldown_min) * 60)
                steps.append(_step(3, "interval", order, _COND_TIME, float(total_sec)))
                order += 1
            else:
                steps.append(_step(1, "warmup", order, _COND_TIME, warmup_min * 60))
                order += 1
                inner = _build_main(main_set, tolerance, 1)
                if repeat > 1:
                    steps.append(repeat_group(order, repeat, inner))
                    order += 1
                else:
                    for i, s in enumerate(inner):
                        s["stepOrder"] = order + i
                    steps.extend(inner)
                    order += len(inner)

        steps.append(_lap_cooldown(order))

        return {
            "workoutName":     spec.get("name", "Workout"),
            "description":     spec.get("description"),
            "sportType":       _SPORT,
            "workoutSegments": [{
                "segmentOrder": 1,
                "sportType":    _SPORT,
                "workoutSteps": steps,
            }],
        }


_builder = RunningBuilder()


@mcp.tool()
def create_running_workout(workout_json: str) -> str:
    """
    Create a structured running workout in Garmin Connect.

    Quality sessions (T / M / I pace) — distance-based warmup/cooldown:
    {
      "name": "Limiar — 3×14' T",
      "description": "optional",
      "warmup_km": 2, "warmup_pace": ["5:26", "5:59"],
      "main_set": [
        {"type": "repeat", "repeat": 3, "steps": [
          {"type": "interval", "minutes": 14, "pace": "4:31"},
          {"type": "recovery", "minutes": 2}
        ]}
      ],
      "cooldown_km": 1, "cooldown_pace": ["5:26", "5:59"],
      "pace_tolerance_sec": 5
    }

    Easy / long runs — distance-based with pace zone:
    {"name": "Rodagem — 12 km", "main_km": 12, "main_pace": ["5:26", "5:59"]}

    Time-based (run/walk, no pace guidance):
    {
      "name": "Run/Walk",
      "warmup_minutes": 5,
      "main_set": [{"type": "interval", "minutes": 30}],
      "cooldown_minutes": 5
    }

    pace format: "M:SS" per km. pace_tolerance_sec: ±s around target (default 10).
    All workouts end with a lap-button cooldown step.
    """
    try:
        spec = json.loads(workout_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})
    return serialize(_builder.create(spec))


@mcp.tool()
def update_running_workout(workout_id: str, workout_json: str) -> str:
    """
    Update an existing running workout in place (PUT).
    Same schema as create_running_workout. Preserves workout ID and calendar scheduling.
    """
    try:
        spec = json.loads(workout_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})
    return serialize(_builder.update(workout_id, spec))
