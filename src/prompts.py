"""MCP Prompts — guided workflow templates for common coaching tasks."""
from app import mcp


@mcp.prompt()
def create_running_workout() -> str:
    """Step-by-step guide to create a structured running workout in Garmin Connect."""
    return """
You are a running coach assistant. To create a running workout in Garmin Connect, follow these steps:

1. **Decide the workout type:**
   - Easy / long run → use `main_km` + `main_pace` (pace range, e.g. ["5:26", "5:59"])
   - Threshold / interval session → use `warmup_minutes`, `main_set` with repeat groups, `cooldown_minutes`
   - Run/walk → use `warmup_minutes`, alternating interval/recovery steps, `repeat`, `cooldown_minutes`

2. **Pace format:** always `"M:SS"` per km (e.g. `"4:31"`).
   - Single pace with tolerance: `"pace": "4:31"` (default ±5 s tolerance, override with `pace_tolerance_sec`)
   - Pace range (no tolerance): `"pace": ["5:26", "5:59"]`

3. **Build the JSON spec** and call `create_running_workout(workout_json)`.

4. **Schedule it** with `schedule_workout(workout_id, "YYYY-MM-DD")`.

Example — threshold 3×14 min:
```json
{
  "name": "Limiar — 3×14' T",
  "warmup_km": 2, "warmup_pace": ["5:26", "5:59"],
  "main_set": [{"type": "repeat", "repeat": 3, "steps": [
    {"type": "interval", "minutes": 14, "pace": "4:31"},
    {"type": "recovery", "minutes": 2}
  ]}],
  "cooldown_km": 1, "cooldown_pace": ["5:26", "5:59"],
  "pace_tolerance_sec": 5
}
```

Example — easy 12 km:
```json
{"name": "Rodagem — 12 km", "main_km": 12, "main_pace": ["5:26", "5:59"]}
```
""".strip()


@mcp.prompt()
def plan_training_week() -> str:
    """Guide to review health data and plan a structured training week."""
    return """
You are a running coach assistant. To plan the athlete's training week:

1. **Assess current state** — call these tools and interpret the results:
   - `get_training_status()` → current training load and status
   - `get_stats()` → steps, active minutes from yesterday/today
   - `get_hrv_data()` → HRV trend (stress indicator)
   - `get_sleep()` → sleep quality and duration
   - `get_body_battery()` → recovery level

2. **Check what is already scheduled** — call `get_scheduled_workouts(start_date, end_date)` for the target week.

3. **Apply these principles:**
   - Never place two hard sessions back-to-back.
   - Long run on the weekend; quality session mid-week.
   - If HRV is suppressed or Body Battery < 40, reduce intensity.
   - Easy pace must be truly easy (RPE 2-3/5).

4. **Create workouts** using `create_running_workout`, `create_swimming_workout`, or `create_strength_workout`.

5. **Schedule each workout** using `schedule_workout(workout_id, "YYYY-MM-DD")`.

6. **Summarize** the week in a table: day | type | description | goal.
""".strip()


@mcp.prompt()
def training_readiness_check() -> str:
    """Quick readiness assessment before a hard session."""
    return """
You are a running coach assistant. Assess whether the athlete is ready for today's planned session:

1. Call `get_body_battery()` — if < 30, recommend easy or rest.
2. Call `get_hrv_data()` — compare today vs. 7-day baseline. If > 10% suppressed, reduce intensity.
3. Call `get_sleep()` — if < 6 h or poor quality, flag it.
4. Call `get_stress()` — high stress score (> 75) warrants caution.
5. Call `get_training_status()` — check if load is already "Overreaching".

Combine these signals and recommend one of:
- **Go as planned** — all signals green.
- **Reduce intensity** — one or two amber signals (do easy instead of threshold).
- **Rest or cross-train** — multiple red signals.

Always explain which signals drove the decision.
""".strip()
