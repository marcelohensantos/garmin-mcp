import json
from datetime import date, datetime

import auth
from app import mcp
from garminconnect.workout import (
    RunningWorkout,
    WorkoutSegment,
    create_cooldown_step,
    create_interval_step,
    create_recovery_step,
    create_repeat_group,
    create_warmup_step,
)


# ---------------------------------------------------------------------------
# Pace helpers
# ---------------------------------------------------------------------------

def _pace_target(pace: str, tolerance_sec: int = 10) -> dict:
    """Build a pace-zone target dict from a 'M:SS /km' string with ±tolerance.

    Garmin pace.zone uses seconds-per-meter: slower pace = higher value.
    targetValueOne = slow bound, targetValueTwo = fast bound.
    """
    parts = pace.strip().split(":")
    total_sec = int(parts[0]) * 60 + int(parts[1])  # s/km
    slow_sm = round((total_sec + tolerance_sec) / 1000, 6)
    fast_sm = round((total_sec - tolerance_sec) / 1000, 6)
    return {
        "targetType": {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone",
            "displayOrder": 6,
        },
        "targetValueOne": slow_sm,
        "targetValueTwo": fast_sm,
    }


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

_LAP_BUTTON_CONDITION = {
    "conditionTypeId": 1,
    "conditionTypeKey": "lap.button",
    "displayOrder": 1,
    "displayable": True,
}


def _lap_cooldown(step_order: int):
    """Cooldown step that ends when the user presses the lap button."""
    step = create_cooldown_step(0, step_order)
    step.endCondition      = _LAP_BUTTON_CONDITION
    step.endConditionValue = None
    return step


def _is_simple_easy(main_set: list[dict], repeat: int) -> bool:
    """True when the workout is a single no-pace interval (pure easy run)."""
    return repeat == 1 and len(main_set) == 1 and not main_set[0].get("pace")


# ---------------------------------------------------------------------------
# Step builder
# ---------------------------------------------------------------------------

def _build_single_step(s: dict, order: int):
    """Build one executable step from a spec dict."""
    stype    = s.get("type", "interval")
    minutes  = float(s.get("minutes", 0))
    seconds_val = float(s.get("seconds", 0))
    duration = minutes * 60 + seconds_val
    pace     = s.get("pace")
    target   = _pace_target(pace) if pace else {}

    if stype == "interval":
        step = create_interval_step(duration, order, target.get("targetType"))
        if target:
            step.targetType = target["targetType"]
            step.model_extra["targetValueOne"] = target["targetValueOne"]
            step.model_extra["targetValueTwo"] = target["targetValueTwo"]
    elif stype == "recovery":
        step = create_recovery_step(duration, order)
    else:
        step = create_interval_step(duration, order)
    return step


def _step_duration(s: dict) -> float:
    """Total duration in seconds for a step spec, expanding nested repeats."""
    if s.get("type") == "repeat":
        inner = sum(
            float(ns.get("minutes", 0)) * 60 + float(ns.get("seconds", 0))
            for ns in s.get("steps", [])
        )
        return inner * int(s.get("repeat", 1))
    return float(s.get("minutes", 0)) * 60 + float(s.get("seconds", 0))


def _build_steps(main_set: list[dict], repeat: int, step_order_start: int) -> list:
    """Build the main set steps, with optional outer repeat group.

    main_set items may be regular steps or nested repeat blocks:
      {"type": "repeat", "repeat": 6, "steps": [...]}
    """
    inner = []
    order = 1
    for s in main_set:
        if s.get("type") == "repeat":
            nested = [_build_single_step(ns, i + 1) for i, ns in enumerate(s.get("steps", []))]
            inner.append(create_repeat_group(int(s.get("repeat", 1)), nested, order))
        else:
            inner.append(_build_single_step(s, order))
        order += 1

    if repeat > 1:
        return [create_repeat_group(repeat, inner, step_order_start)]
    return [
        s.__class__(**{**s.model_dump(exclude_none=True), "stepOrder": step_order_start + i})
        for i, s in enumerate(inner)
    ]


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@mcp.tool()
def create_running_workout(workout_json: str) -> str:
    """
    Create a structured running workout in Garmin Connect.

    workout_json schema:
    {
      "name": "Threshold 3x14min",
      "description": "optional",
      "warmup_minutes": 15,
      "main_set": [
        {"type": "interval", "minutes": 14, "pace": "4:31"},
        {"type": "recovery", "minutes": 2}
      ],
      "repeat": 3,
      "cooldown_minutes": 10
    }

    pace format: "M:SS" per km (e.g. "4:31").

    Step structure rules:
    - All workouts end with a cooldown step using lap-button-press (open-ended).
    - Simple easy runs (single no-pace interval): warmup + cooldown are merged into
      the interval; only one interval step + lap cooldown are created.
    - All other workouts: warmup (time-based) + main set + lap cooldown.

    Returns the created workout id and name.
    """
    try:
        spec = json.loads(workout_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    name         = spec.get("name", "Workout")
    description  = spec.get("description")
    warmup_min   = float(spec.get("warmup_minutes", 10))
    cooldown_min = float(spec.get("cooldown_minutes", 10))
    main_set     = spec.get("main_set", [])
    repeat       = int(spec.get("repeat", 1))

    if _is_simple_easy(main_set, repeat):
        # Merge warmup + interval + cooldown into a single continuous interval
        s         = main_set[0]
        total_sec = int((warmup_min + float(s.get("minutes", 0)) + cooldown_min) * 60)
        run_step  = create_interval_step(total_sec, step_order=1)
        lap_cd    = _lap_cooldown(step_order=2)
        all_steps = [run_step, lap_cd]
    else:
        warmup    = create_warmup_step(warmup_min * 60, step_order=1)
        main      = _build_steps(main_set, repeat, step_order_start=2)
        lap_cd    = _lap_cooldown(step_order=2 + len(main))
        all_steps = [warmup, *main, lap_cd]
        total_sec = int(
            warmup_min * 60
            + sum(_step_duration(s) for s in main_set) * repeat
            + cooldown_min * 60
        )

    workout = RunningWorkout(
        workoutName=name,
        description=description,
        estimatedDurationInSecs=total_sec,
        workoutSegments=[
            WorkoutSegment(
                segmentOrder=1,
                sportType={"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
                workoutSteps=all_steps,
            )
        ],
    )

    result     = auth.get_client().upload_running_workout(workout)
    workout_id = result.get("workoutId") or result.get("workout", {}).get("workoutId")
    return json.dumps({"workoutId": workout_id, "name": name, "estimatedDurationSecs": total_sec})


@mcp.tool()
def schedule_workout(workout_id: str, date: str) -> str:
    """
    Schedule an existing workout to the Garmin calendar on date (YYYY-MM-DD).
    Returns the scheduled workout details.
    """
    result = auth.get_client().schedule_workout(workout_id, date)
    return json.dumps(result, default=str)


@mcp.tool()
def get_workouts(limit: int = 20) -> str:
    """Return the most recent workouts saved in Garmin Connect."""
    data = auth.get_client().get_workouts(0, limit)
    return json.dumps(data, default=str, indent=2)


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
    return json.dumps(results, default=str)
