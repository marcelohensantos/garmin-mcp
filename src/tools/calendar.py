"""Garmin workout calendar tools — sport-agnostic CRUD."""
import json
from datetime import datetime

import auth
from app import mcp
from utils import serialize


@mcp.tool()
def schedule_workout(workout_id: str, date: str) -> str:
    """Schedule an existing workout on the Garmin calendar (YYYY-MM-DD)."""
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
    Dates in YYYY-MM-DD format.
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
        current = (current.replace(year=current.year + 1, month=1)
                   if current.month == 12
                   else current.replace(month=current.month + 1))

    results = []
    for year, month in sorted(months):
        data  = client.get_scheduled_workouts(year, month)
        items = data if isinstance(data, list) else (data or {}).get("calendarItems", []) or []
        for item in items:
            date_str = item.get("date") or item.get("calendarDate", "")
            if not date_str:
                continue
            try:
                item_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
            if start <= item_date <= end:
                results.append({
                    "date":        date_str[:10],
                    "workoutId":   item.get("workoutId"),
                    "workoutName": item.get("workoutName") or item.get("title", ""),
                    "sportType":   item.get("sportTypeKey") or item.get("workoutTypeKey", ""),
                })

    results.sort(key=lambda x: x["date"])
    return serialize(results)
