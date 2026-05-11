import json
from datetime import date
from pathlib import Path


def today() -> str:
    return date.today().isoformat()


def export_dir() -> Path:
    d = Path.home() / "garmin_exports"
    d.mkdir(exist_ok=True)
    return d


def serialize(data: object) -> str:
    """Serialize any Garmin API response to indented JSON."""
    return json.dumps(data, default=str, indent=2)
