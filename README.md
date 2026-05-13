# garmin-mcp

MCP server that exposes Garmin Connect data to Claude (Desktop, Code, or any MCP client).

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

> **Switching accounts?** If you previously logged in with a different Garmin account,
> clear the cache before running `make check`:
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

## Available tools

### Activities

| Tool | Description |
|------|-------------|
| `get_activities` | Most recent N activities; optional `activity_type` filter (e.g. `running`, `strength_training`, `swimming`) |
| `get_activities_by_date` | Activities in a date range; same optional `activity_type` filter |
| `get_activity_details` | Full details for one activity |
| `export_activity` | Download GPX / TCX / FIT / CSV |
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
| `create_running_workout` | Structured running workout — pace zones, repeat groups, lap-button cooldown |
| `create_swimming_workout` | Structured pool swimming workout — distance-based steps, stroke types, repeat groups |
| `create_strength_workout` | Strength session — exercises grouped as repeat sets with weight and rest |
| `schedule_workout` | Schedule an existing workout on the Garmin calendar |
| `get_workouts` | List saved workouts |
| `delete_workout` | Delete a workout by ID |
| `get_scheduled_workouts` | List scheduled workouts in a date range |

### Plans

| Tool | Description |
|------|-------------|
| `save_plan` | Save a training plan JSON to `~/devel/garmin/data/` for later reference by agents |

### Profile & devices

| Tool | Description |
|------|-------------|
| `get_user_profile` | Account profile |
| `get_devices` | Linked Garmin devices |
| `get_gear` | Shoes, bikes, and other gear |

## Project layout

```
src/
├── app.py              # FastMCP instance
├── auth.py             # Garmin client singleton
├── utils.py            # Shared helpers (today, serialize, export_dir)
├── server.py           # Entry point
├── check.py            # Connectivity smoke test
└── tools/
    ├── activities.py   # Activity tools (with activity_type filter)
    ├── health.py       # Health & wellness tools
    ├── training.py     # Training & fitness tools
    ├── workouts.py     # Running workout creation and calendar tools
    ├── swimming.py     # Swimming workout creation
    ├── strength.py     # Strength workout creation
    ├── plans.py        # save_plan — persist plans to data/
    └── profile.py      # Profile & devices tools

tests/
├── unit/               # Mocked tests, no network required
└── integration/        # Live tests against Garmin Connect API
```

## Running tests

```bash
# Unit tests (no credentials needed)
make test

# Integration tests (requires real Garmin account)
make test-integration
```

## Notes

- Exported files land in `~/garmin_exports/`.
- MFA accounts: set `return_on_mfa=True` in `auth.py` and handle the prompt manually.
- The first run triggers a full login; subsequent runs reuse cached OAuth tokens.
- `create_running_workout` pace targets use `pace.zone` (min/km display on device).
  Simple easy runs (single step, no pace) merge warmup + run + cooldown into one interval.
  Run/walk and other repeat-group workouts work with no pace target — omit the `pace` field.
- `create_swimming_workout` uses `sportTypeId: 4` (the library enum is incorrect — raw dict is used).
- `create_strength_workout` uses `sportTypeId: 5` and the generic `upload_workout()` method.
  Set `weight_kg: -1.0` for bodyweight exercises.
- `get_activities` / `get_activities_by_date` filter by `activityType.typeKey` client-side.
  Use a larger `limit` when filtering to avoid truncation before the filter is applied.
- `save_plan` always writes to `~/devel/garmin/data/` — the directory is created if absent.
