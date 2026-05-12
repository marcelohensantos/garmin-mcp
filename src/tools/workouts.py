import json
from datetime import datetime

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
from utils import serialize


# ---------------------------------------------------------------------------
# Pace helpers
# ---------------------------------------------------------------------------

def _pace_target(pace: str, tolerance_sec: int = 10) -> dict:
    """Build a pace-zone target dict from a 'M:SS /km' string with ±tolerance.

    Garmin pace.zone uses seconds-per-meter: slower pace = higher value.
    targetValueOne = slow bound, targetValueTwo = fast bound.
    """
    minutes, seconds = pace.strip().split(":")
    total_sec = int(minutes) * 60 + int(seconds)  # s/km
    return {
        "targetType": {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone",
            "displayOrder": 6,
        },
        "targetValueOne": round((total_sec + tolerance_sec) / 1000, 6),
        "targetValueTwo": round((total_sec - tolerance_sec) / 1000, 6),
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
    return (
        repeat == 1
        and len(main_set) == 1
        and main_set[0].get("type") != "repeat"
        and not main_set[0].get("pace")
    )


# ---------------------------------------------------------------------------
# Step builder
# ---------------------------------------------------------------------------

def _build_single_step(spec: dict, order: int):
    """Build one executable step from a spec dict."""
    stype    = spec.get("type", "interval")
    duration = float(spec.get("minutes", 0)) * 60 + float(spec.get("seconds", 0))
    pace     = spec.get("pace")
    target   = _pace_target(pace) if pace else {}

    if stype == "interval":
        step = create_interval_step(duration, order, target.get("targetType"))
        if target:
            step.targetType                    = target["targetType"]
            step.model_extra["targetValueOne"] = target["targetValueOne"]
            step.model_extra["targetValueTwo"] = target["targetValueTwo"]
    elif stype == "recovery":
        step = create_recovery_step(duration, order)
    else:
        step = create_interval_step(duration, order)
    return step


def _step_duration(spec: dict) -> float:
    """Total duration in seconds for a step spec, expanding nested repeats."""
    if spec.get("type") == "repeat":
        inner = sum(
            float(s.get("minutes", 0)) * 60 + float(s.get("seconds", 0))
            for s in spec.get("steps", [])
        )
        return inner * int(spec.get("repeat", 1))
    return float(spec.get("minutes", 0)) * 60 + float(spec.get("seconds", 0))


def _build_steps(main_set: list[dict], repeat: int, step_order_start: int) -> list:
    """Build the main set steps, with optional outer repeat group.

    main_set items may be regular steps or nested repeat blocks:
      {"type": "repeat", "repeat": 6, "steps": [...]}
    """
    inner = []
    for order, spec in enumerate(main_set, start=1):
        if spec.get("type") == "repeat":
            nested = [_build_single_step(s, i + 1) for i, s in enumerate(spec.get("steps", []))]
            inner.append(create_repeat_group(int(spec.get("repeat", 1)), nested, order))
        else:
            inner.append(_build_single_step(spec, order))

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
        {"type": "recovery", "minutes": 2},
        {"type": "repeat", "repeat": 6, "steps": [
          {"type": "interval", "seconds": 20, "pace": "3:54"},
          {"type": "recovery", "minutes": 1, "seconds": 40}
        ]}
      ],
      "repeat": 3,
      "cooldown_minutes": 10
    }

    pace format: "M:SS" per km (e.g. "4:31"). Target type: pace.zone (min/km display on device).

    Step structure rules:
    - All workouts end with a cooldown step using lap-button-press (open-ended).
    - Simple easy runs (single no-pace interval): warmup + cooldown are merged into
      the interval; only one interval step + lap cooldown are created.
    - All other workouts: warmup (time-based) + main set + lap cooldown.
    - Nested repeat blocks produce a RepeatGroup on the device.

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
        s         = main_set[0]
        total_sec = int((warmup_min + float(s.get("minutes", 0)) + cooldown_min) * 60)
        all_steps = [create_interval_step(total_sec, step_order=1), _lap_cooldown(step_order=2)]
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
    return serialize({"workoutId": workout_id, "name": name, "estimatedDurationSecs": total_sec})


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
