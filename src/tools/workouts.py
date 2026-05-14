import json
from datetime import datetime

import auth
from app import mcp
from utils import serialize


# ---------------------------------------------------------------------------
# Pace helpers
# ---------------------------------------------------------------------------

def _pace_target(pace: str, tolerance_sec: int = 10) -> dict:
    """Build a pace-zone target dict from a 'M:SS /km' string with ±tolerance.

    Garmin pace.zone uses m/s: faster pace = higher value.
    targetValueOne = fast bound (m/s), targetValueTwo = slow bound (m/s).
    """
    minutes, seconds = pace.strip().split(":")
    total_sec = int(minutes) * 60 + int(seconds)  # s/km
    return {
        "targetType": {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone",
            "displayOrder": 6,
        },
        "targetValueOne": round(1000 / (total_sec - tolerance_sec), 7),  # fast bound m/s
        "targetValueTwo": round(1000 / (total_sec + tolerance_sec), 7),  # slow bound m/s
    }


def _pace_range_target(pace_fast: str, pace_slow: str) -> dict:
    """Build a pace-zone target from explicit fast/slow pace bounds (no tolerance)."""
    def to_ms(p):
        m, s = p.strip().split(":")
        return round(1000 / (int(m) * 60 + int(s)), 7)
    return {
        "targetType": {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone",
            "displayOrder": 6,
        },
        "targetValueOne": to_ms(pace_fast),
        "targetValueTwo": to_ms(pace_slow),
    }


# ---------------------------------------------------------------------------
# Raw step dict builders
# ---------------------------------------------------------------------------

_STROKE = {"strokeTypeId": 0, "strokeTypeKey": None, "displayOrder": 0}
_EQUIP  = {"equipmentTypeId": 0, "equipmentTypeKey": None, "displayOrder": 0}
_KM     = {"unitId": 2, "unitKey": "kilometer", "factor": 100000.0}

_NO_TARGET = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1}
_PACE_ZONE = {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone", "displayOrder": 6}

_COND_TIME = {"conditionTypeId": 2, "conditionTypeKey": "time",      "displayOrder": 2, "displayable": True}
_COND_DIST = {"conditionTypeId": 3, "conditionTypeKey": "distance",  "displayOrder": 3, "displayable": True}
_COND_LAP  = {"conditionTypeId": 1, "conditionTypeKey": "lap.button","displayOrder": 1, "displayable": True}
_COND_ITER = {"conditionTypeId": 7, "conditionTypeKey": "iterations","displayOrder": 7, "displayable": False}


def _raw_step(step_type_id: int, step_type_key: str, step_order: int,
              end_cond: dict, end_value, child_step_id=None,
              target_type: dict = None, val_one=None, val_two=None,
              pref_unit: dict = None) -> dict:
    s = {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": step_type_id, "stepTypeKey": step_type_key,
                     "displayOrder": step_type_id},
        "endCondition": end_cond,
        "endConditionValue": end_value,
        "targetType": target_type or _NO_TARGET,
        "targetValueOne": val_one,
        "targetValueTwo": val_two,
        "strokeType": _STROKE,
        "equipmentType": _EQUIP,
    }
    if child_step_id is not None:
        s["childStepId"] = child_step_id
    if pref_unit:
        s["preferredEndConditionUnit"] = pref_unit
    return s


def _raw_warmup_distance(step_order: int, distance_m: float,
                          pace_fast: str = None, pace_slow: str = None) -> dict:
    tgt = _pace_range_target(pace_fast, pace_slow) if pace_fast and pace_slow else {}
    return _raw_step(1, "warmup", step_order,
                     _COND_DIST, distance_m,
                     target_type=tgt.get("targetType", _NO_TARGET),
                     val_one=tgt.get("targetValueOne"),
                     val_two=tgt.get("targetValueTwo"),
                     pref_unit=_KM)


def _raw_interval_distance(step_order: int, distance_m: float,
                            pace_fast: str = None, pace_slow: str = None) -> dict:
    tgt = _pace_range_target(pace_fast, pace_slow) if pace_fast and pace_slow else {}
    return _raw_step(3, "interval", step_order,
                     _COND_DIST, distance_m,
                     target_type=tgt.get("targetType", _NO_TARGET),
                     val_one=tgt.get("targetValueOne"),
                     val_two=tgt.get("targetValueTwo"),
                     pref_unit=_KM)


def _raw_cooldown_distance(step_order: int, distance_m: float,
                            pace_fast: str = None, pace_slow: str = None) -> dict:
    tgt = _pace_range_target(pace_fast, pace_slow) if pace_fast and pace_slow else {}
    return _raw_step(2, "cooldown", step_order,
                     _COND_DIST, distance_m,
                     target_type=tgt.get("targetType", _NO_TARGET),
                     val_one=tgt.get("targetValueOne"),
                     val_two=tgt.get("targetValueTwo"),
                     pref_unit=_KM)


def _raw_lap_cooldown(step_order: int) -> dict:
    return _raw_step(2, "cooldown", step_order, _COND_LAP, None)


def _raw_interval(step_order: int, duration_sec: float, child_step_id: int,
                  pace: str = None, tolerance_sec: int = 10) -> dict:
    tgt = _pace_target(pace, tolerance_sec) if pace else {}
    return _raw_step(3, "interval", step_order,
                     _COND_TIME, duration_sec,
                     child_step_id=child_step_id,
                     target_type=tgt.get("targetType", _NO_TARGET),
                     val_one=tgt.get("targetValueOne"),
                     val_two=tgt.get("targetValueTwo"))


def _raw_recovery(step_order: int, duration_sec: float, child_step_id: int) -> dict:
    return _raw_step(4, "recovery", step_order,
                     _COND_TIME, duration_sec,
                     child_step_id=child_step_id)


def _raw_repeat_group(step_order: int, n: int, steps: list,
                       skip_last_rest: bool = True) -> dict:
    return {
        "type": "RepeatGroupDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6},
        "childStepId": 1,
        "numberOfIterations": n,
        "endCondition": _COND_ITER,
        "endConditionValue": float(n),
        "skipLastRestStep": skip_last_rest,
        "smartRepeat": False,
        "workoutSteps": steps,
    }


# ---------------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------------

def _is_simple_easy(main_set: list[dict], repeat: int) -> bool:
    """True when the workout is a single no-pace interval (pure easy run)."""
    return (
        repeat == 1
        and len(main_set) == 1
        and main_set[0].get("type") != "repeat"
        and not main_set[0].get("pace")
    )


def _build_main_steps(main_set: list[dict], tolerance_sec: int,
                      step_order_start: int) -> list[dict]:
    """Build raw step dicts for a main_set list, starting at step_order_start."""
    steps = []
    order = step_order_start
    for spec in main_set:
        if spec.get("type") == "repeat":
            inner_steps = []
            inner_order = order + 1
            for s in spec.get("steps", []):
                dur   = float(s.get("minutes", 0)) * 60 + float(s.get("seconds", 0))
                stype = s.get("type", "interval")
                if stype == "interval":
                    inner_steps.append(_raw_interval(inner_order, dur, 1,
                                                     s.get("pace"), tolerance_sec))
                else:
                    inner_steps.append(_raw_recovery(inner_order, dur, 1))
                inner_order += 1
            steps.append(_raw_repeat_group(order, int(spec.get("repeat", 1)), inner_steps))
        elif spec.get("type") == "interval":
            dur = float(spec.get("minutes", 0)) * 60 + float(spec.get("seconds", 0))
            steps.append(_raw_interval(order, dur, None, spec.get("pace"), tolerance_sec))
        elif spec.get("type") == "recovery":
            dur = float(spec.get("minutes", 0)) * 60 + float(spec.get("seconds", 0))
            steps.append(_raw_recovery(order, dur, None))
        order += 1
    return steps


def _build_workout_payload(spec: dict) -> dict:
    """Build the full workout payload dict from a spec (used by create and update)."""
    name          = spec.get("name", "Workout")
    description   = spec.get("description")
    main_set      = spec.get("main_set", [])
    repeat        = int(spec.get("repeat", 1))
    tolerance_sec = int(spec.get("pace_tolerance_sec", 10))
    warmup_km     = spec.get("warmup_km")
    cooldown_km   = spec.get("cooldown_km")
    warmup_pace   = spec.get("warmup_pace")
    cooldown_pace = spec.get("cooldown_pace")
    main_km       = spec.get("main_km")
    main_pace     = spec.get("main_pace")

    steps = []
    order = 1

    if warmup_km is not None or cooldown_km is not None or main_km is not None:
        if warmup_km:
            steps.append(_raw_warmup_distance(order, float(warmup_km) * 1000,
                                              warmup_pace[0] if warmup_pace else None,
                                              warmup_pace[1] if warmup_pace else None))
            order += 1
        if main_km:
            steps.append(_raw_interval_distance(order, float(main_km) * 1000,
                                                main_pace[0] if main_pace else None,
                                                main_pace[1] if main_pace else None))
            order += 1
        elif main_set:
            raw = _build_main_steps(main_set, tolerance_sec, order)
            steps.extend(raw)
            order += len(raw)
        if cooldown_km:
            steps.append(_raw_cooldown_distance(order, float(cooldown_km) * 1000,
                                                cooldown_pace[0] if cooldown_pace else None,
                                                cooldown_pace[1] if cooldown_pace else None))
            order += 1
    else:
        warmup_min   = float(spec.get("warmup_minutes", 10))
        cooldown_min = float(spec.get("cooldown_minutes", 10))
        if _is_simple_easy(main_set, repeat):
            s         = main_set[0]
            total_sec = int((warmup_min + float(s.get("minutes", 0)) + cooldown_min) * 60)
            steps.append(_raw_step(3, "interval", order, _COND_TIME, float(total_sec)))
            order += 1
        else:
            steps.append(_raw_step(1, "warmup", order, _COND_TIME, warmup_min * 60))
            order += 1
            inner = _build_main_steps(main_set, tolerance_sec, 1)
            if repeat > 1:
                steps.append(_raw_repeat_group(order, repeat, inner))
                order += 1
            else:
                for i, s in enumerate(inner):
                    s["stepOrder"] = order + i
                steps.extend(inner)
                order += len(inner)

    steps.append(_raw_lap_cooldown(order))

    return {
        "workoutName": name,
        "description": description,
        "sportType": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
        "workoutSegments": [{
            "segmentOrder": 1,
            "sportType": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
            "workoutSteps": steps,
        }],
    }


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@mcp.tool()
def create_running_workout(workout_json: str) -> str:
    """
    Create a structured running workout in Garmin Connect.

    workout_json schema:

    Quality sessions (T / M / I pace) — distance-based warmup/cooldown with pace zone:
    {
      "name": "Limiar — 3×14' T",
      "description": "optional",
      "warmup_km": 2,
      "warmup_pace": ["5:26", "5:59"],
      "main_set": [
        {"type": "repeat", "repeat": 3, "steps": [
          {"type": "interval", "minutes": 14, "pace": "4:31"},
          {"type": "recovery", "minutes": 2}
        ]}
      ],
      "cooldown_km": 1,
      "cooldown_pace": ["5:26", "5:59"],
      "pace_tolerance_sec": 5
    }

    Easy / long runs — distance-based with E zone pace:
    {
      "name": "Rodagem Fácil — 12 km",
      "main_km": 12,
      "main_pace": ["5:26", "5:59"]
    }

    Run/walk or time-based easy (no pace guidance):
    {
      "name": "Easy 60min",
      "warmup_minutes": 1,
      "main_set": [{"type": "interval", "minutes": 58}],
      "cooldown_minutes": 1
    }

    pace format: "M:SS" per km. pace_tolerance_sec: ±seconds around target (default 10).
    warmup_pace / cooldown_pace / main_pace: [fast_pace, slow_pace] for pace zone bounds.
    All workouts end with an open lap-button cooldown step.

    Returns the created workout id and name.
    """
    try:
        spec = json.loads(workout_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    payload    = _build_workout_payload(spec)
    result     = auth.get_client().upload_workout(payload)
    workout_id = result.get("workoutId") or result.get("workout", {}).get("workoutId")
    return serialize({"workoutId": workout_id, "name": spec.get("name", "Workout")})


@mcp.tool()
def update_running_workout(workout_id: str, workout_json: str) -> str:
    """
    Update an existing running workout in place (PUT).
    Accepts the same workout_json schema as create_running_workout.
    Preserves the workout ID and all calendar scheduling — no need to reschedule.

    Returns the workout id, name, and updated: true.
    """
    try:
        spec = json.loads(workout_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    payload                = _build_workout_payload(spec)
    payload["workoutId"]   = int(workout_id)
    client                 = auth.get_client()
    client.client.put("connectapi", f"/workout-service/workout/{workout_id}", json=payload)
    return serialize({"workoutId": int(workout_id), "name": spec.get("name", "Workout"),
                      "updated": True})


@mcp.tool()
def schedule_workout(workout_id: str, date: str) -> str:
    """
    Schedule an existing workout to the Garmin calendar on date (YYYY-MM-DD).
    Returns the scheduled workout details.
    """
    return serialize(auth.get_client().schedule_workout(workout_id, date))


@mcp.tool()
def get_workouts(limit: int = 20) -> str:
    """Return the most recent workouts saved in Garmin Connect."""
    return serialize(auth.get_client().get_workouts(0, limit))


@mcp.tool()
def delete_workout(workout_id: str) -> str:
    """Delete a workout from Garmin Connect by its ID."""
    auth.get_client().delete_workout(workout_id)
    return json.dumps({"deleted": workout_id})


@mcp.tool()
def get_scheduled_workouts(start_date: str, end_date: str) -> str:
    """
    Return workouts scheduled on the Garmin calendar between start_date and end_date (inclusive).
    Dates in YYYY-MM-DD format. Useful for agents to check which days already have workouts
    planned before prescribing sessions for other sports.

    Returns a list of {date, workoutId, workoutName, sportType} sorted by date.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end   = datetime.strptime(end_date,   "%Y-%m-%d").date()
    except ValueError as e:
        return json.dumps({"error": f"Invalid date format: {e}"})

    if start > end:
        return json.dumps({"error": "start_date must be <= end_date"})

    client  = auth.get_client()
    months: set[tuple[int, int]] = set()
    current = start.replace(day=1)
    while current <= end.replace(day=1):
        months.add((current.year, current.month))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    results = []
    for year, month in sorted(months):
        data  = client.get_scheduled_workouts(year, month)
        items = data if isinstance(data, list) else (data or {}).get("calendarItems", []) or []
        for item in items:
            item_date_str = item.get("date") or item.get("calendarDate", "")
            if not item_date_str:
                continue
            try:
                item_date = datetime.strptime(item_date_str[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
            if start <= item_date <= end:
                results.append({
                    "date":        item_date_str[:10],
                    "workoutId":   item.get("workoutId"),
                    "workoutName": item.get("workoutName") or item.get("title", ""),
                    "sportType":   item.get("sportTypeKey") or item.get("workoutTypeKey", ""),
                })

    results.sort(key=lambda x: x["date"])
    return serialize(results)
