# garmin-mcp

[![CI](https://github.com/marcelohensantos/garmin-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/marcelohensantos/garmin-mcp/actions/workflows/ci.yml)

MCP server that exposes Garmin Connect data and workout management to AI agents.
Supports tools, resources, and prompts — covering reading health data, creating and
scheduling structured workouts, and guided coaching workflows.

## Setup

### 1. Clone & install

```bash
git clone https://github.com/marcelohensantos/garmin-mcp
cd garmin-mcp
python3 -m venv .venv
make install
```

### 2. Configure credentials

Create `.env`:

```env
GARMIN_EMAIL=seu@email.com
GARMIN_PASSWORD=suasenha
```

OAuth tokens are cached automatically at `~/.garminconnect/` after the first login.

> **Switching accounts?** Clear the cache before running `make check`:
> ```bash
> make clean-auth
> ```

### 3. Verify connection

```bash
make check
```

### 4. Configure your MCP client

**Claude Desktop** — edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "garmin": {
      "command": "/path/to/garmin-mcp/.venv/bin/python",
      "args": ["/path/to/garmin-mcp/src/server.py"]
    }
  }
}
```

**Claude Code** — add to `.mcp.json` at the project root:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "/path/to/garmin-mcp/.venv/bin/python",
      "args": ["/path/to/garmin-mcp/src/server.py"]
    }
  }
}
```

Restart the client after saving.

---

## Available tools

### Activities

| Tool | Description |
|------|-------------|
| `get_activities` | Most recent N activities; optional `activity_type` filter (`running`, `strength_training`, `swimming`, …) |
| `get_activities_by_date` | Activities in a date range; same optional `activity_type` filter |
| `get_activity_details` | Full details for one activity |
| `export_activity` | Download GPX / TCX / FIT / CSV for one activity |
| `export_activities_csv` | Summary CSV for a date range |

### Health & wellness

| Tool | Description |
|------|-------------|
| `get_stats` | Daily steps, calories, floors |
| `get_heart_rates` | Heart-rate timeline |
| `get_sleep` | Sleep stages and score |
| `get_stress` | Stress levels throughout the day |
| `get_body_battery` | Body Battery charge curve |
| `get_body_composition` | Weight, BMI, body fat |
| `get_hrv_data` | Heart Rate Variability |
| `get_spo2` | Blood oxygen saturation |

### Training & fitness

| Tool | Description |
|------|-------------|
| `get_training_status` | Training load and status |
| `get_personal_records` | All-time PRs |
| `get_vo2max` | VO2 max estimates |

### Workouts & calendar

| Tool | Description |
|------|-------------|
| `create_running_workout` | Structured running workout — pace zones, repeat groups, distance/time-based steps |
| `update_running_workout` | Update an existing running workout in-place via PUT (preserves calendar scheduling) |
| `create_swimming_workout` | Structured pool swimming workout — stroke types, pool length, repeat groups |
| `create_strength_workout` | Strength session — exercises grouped as repeat sets with weight and rest |
| `schedule_workout` | Schedule an existing workout on the Garmin calendar |
| `get_workouts` | List saved workouts |
| `delete_workout` | Delete a workout by ID |
| `get_scheduled_workouts` | List scheduled workouts in a date range |

### Plans

| Tool | Description |
|------|-------------|
| `save_plan` | Persist an agent-generated training plan as JSON to `~/devel/garmin/data/` |

### Profile & devices

| Tool | Description |
|------|-------------|
| `get_user_profile` | Account profile |
| `get_devices` | Linked Garmin devices |
| `get_gear` | Shoes, bikes, and other gear |

---

## Resources

Resources provide persistent context the agent can read without an explicit tool call.

| URI | Contents |
|-----|----------|
| `garmin://athlete/profile` | User profile + all personal records |
| `garmin://health/today` | Today's stats, Body Battery, HRV, and sleep snapshot |

Both resources are cached for 5 minutes to avoid redundant API calls.

---

## Prompts

Guided workflow templates for common coaching tasks.

| Prompt | Purpose |
|--------|---------|
| `create_running_workout` | Step-by-step guide: spec format, pace syntax, examples, schedule call |
| `plan_training_week` | Multi-step protocol: assess recovery data → check calendar → create and schedule workouts |
| `training_readiness_check` | Pre-session readiness: Body Battery, HRV, sleep, stress → go / reduce / rest decision |

---

## Project layout

```
src/
├── server.py           # Entry point — imports all modules to trigger registration
├── app.py              # FastMCP instance (shared across all modules)
├── auth.py             # Garmin client singleton; wraps login errors in GarminAuthError
├── cache.py            # @cached(ttl_seconds) in-memory TTL decorator
├── errors.py           # GarminAPIError hierarchy + tool_guard decorator
├── utils.py            # serialize(), today(), export_dir()
├── resources.py        # MCP resources: athlete/profile, health/today
├── prompts.py          # MCP prompts: create_running_workout, plan_training_week, …
├── check.py            # Connectivity smoke test (make check)
└── tools/
    ├── builder.py      # WorkoutBuilder base class + repeat_group() helper
    ├── running.py      # RunningBuilder + create/update_running_workout
    ├── swimming.py     # SwimmingBuilder + create_swimming_workout
    ├── strength.py     # StrengthBuilder + create_strength_workout
    ├── calendar.py     # schedule, get, delete, get_scheduled workouts
    ├── activities.py   # Activity retrieval, filtering, and export
    ├── health.py       # Health & wellness tools (cached 5 min)
    ├── training.py     # Training status, VO2 max, PRs (cached 5–10 min)
    ├── profile.py      # User profile, devices, gear (cached 10 min)
    └── plans.py        # save_plan — persist plans to data/

tests/
├── unit/               # Mocked — 50 tests, no network required
└── integration/        # Live tests against Garmin Connect API
```

---

## Running tests

```bash
# Unit tests (no credentials needed)
make test

# Integration tests (requires real Garmin account)
make test-integration
```

---

## Notes

- **Caching** — health, training, and profile tools cache responses for 5–10 minutes. If you need fresh data immediately, restart the server.
- **Error types** — API errors are typed: `GarminAuthError`, `GarminRateLimitError`, `GarminNotFoundError`. Tools return `{"error": "...", "type": "..."}` on failure.
- **Exported files** land in `~/garmin_exports/`.
- **MFA accounts** — set `return_on_mfa=True` in `auth.py` and handle the prompt manually.
- **First run** triggers a full OAuth login; subsequent runs reuse cached tokens at `~/.garminconnect/`.
- **Pace zones** — `pace.zone` targets use m/s internally (`targetValueOne > targetValueTwo`). Single pace `"4:31"` applies a tolerance (default ±10 s); range `["5:26", "5:59"]` uses exact bounds.
- **Easy runs** — a single no-pace interval with warmup/cooldown merges into one time step + lap-button cooldown.
- **Distance-based warmup/cooldown** — use `warmup_km` + `warmup_pace: ["fast", "slow"]` for E zone guidance on distance steps.
- **Bodyweight exercises** — set `weight_kg: -1.0` in `create_strength_workout`.
- **Activity filter** — `get_activities` filters by `activityType.typeKey` client-side; use a larger `limit` when filtering to avoid truncation before the filter runs.
- **`save_plan`** always writes to `~/devel/garmin/data/` — the directory is created if absent.
