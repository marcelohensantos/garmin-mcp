import json
from pathlib import Path

from app import mcp
from utils import serialize

_DATA_DIR = Path.home() / "devel" / "garmin" / "data"


@mcp.tool()
def save_plan(filename: str, plan_json: str) -> str:
    """
    Save a training plan JSON to ~/devel/garmin/data/ for later reference.

    filename  : file name including extension, e.g. "running_plan.json"
    plan_json : valid JSON string with the plan content

    Overwrites any existing file with the same name.
    Returns the absolute path where the file was saved.

    Convention:
      running_plan.json   — weekly running plan
      swimming_plan.json  — weekly swimming plan
      strength_plan.json  — weekly strength plan
      coach_plan.json     — unified weekly plan (all sports)
    """
    try:
        parsed = json.loads(plan_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _DATA_DIR / filename
    path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
    return serialize({"saved": str(path)})
