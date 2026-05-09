# garmin-mcp

MCP server that exposes Garmin Connect data to Claude Desktop (or any MCP client).

## Setup

### 1. Clone & install

```bash
git clone <repo-url> garmin-mcp
cd garmin-mcp
python3 -m venv .venv
.venv/bin/pip install mcp garminconnect python-dotenv
```

### 2. Configure credentials

Edit `.env`:

```env
GARMIN_EMAIL=seu@email.com
GARMIN_PASSWORD=suasenha
```

OAuth tokens are cached automatically at `~/.garminconnect/oauth_tokens.json` after the first login.

### 3. Add to Claude Desktop

Open `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows) and add:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "/home/marcelo/devel/garmin-mcp/.venv/bin/python",
      "args": ["/home/marcelo/devel/garmin-mcp/garmin_mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop after saving.

## Available tools

| Tool | Description |
|------|-------------|
| `get_activities` | Most recent N activities |
| `get_activities_by_date` | Activities in a date range |
| `get_activity_details` | Full details for one activity |
| `export_activity` | Download GPX / TCX / FIT / CSV |
| `export_activities_csv` | Summary CSV for a date range |
| `get_stats` | Daily steps, calories, floors |
| `get_heart_rates` | Heart-rate timeline |
| `get_sleep` | Sleep stages and score |
| `get_stress` | Stress levels throughout the day |
| `get_body_battery` | Body Battery charge curve |
| `get_body_composition` | Weight, BMI, body fat |
| `get_hrv_data` | Heart Rate Variability |
| `get_spo2` | Blood oxygen saturation |
| `get_training_status` | Training load and status |
| `get_personal_records` | All-time PRs |
| `get_vo2max` | VO2 max estimates |
| `get_user_profile` | Account profile |
| `get_devices` | Linked Garmin devices |
| `get_gear` | Shoes, bikes, and other gear |

## Notes

- MFA accounts: set `return_on_mfa=True` in the client constructor and handle the prompt manually.
- Exported files land in `~/garmin_exports/`.
