# garmin-mcp

MCP server that exposes Garmin Connect data to Claude (Desktop, Code, or any MCP client).

## Setup

### 1. Clone & install

```bash
git clone <repo-url> garmin-mcp
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
| `get_activities` | Most recent N activities |
| `get_activities_by_date` | Activities in a date range |
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
| `create_running_workout` | Create a structured running workout with pace targets and repeat groups |
| `schedule_workout` | Schedule an existing workout on the Garmin calendar |
| `get_workouts` | List saved workouts |
| `delete_workout` | Delete a workout by ID |
| `get_scheduled_workouts` | List scheduled workouts in a date range |

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
    ├── activities.py   # Activity tools
    ├── health.py       # Health & wellness tools
    ├── training.py     # Training & fitness tools
    ├── workouts.py     # Workout creation and calendar tools
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
