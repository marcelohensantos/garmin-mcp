from datetime import date
from pathlib import Path


def today() -> str:
    return date.today().isoformat()


def export_dir() -> Path:
    d = Path.home() / "garmin_exports"
    d.mkdir(exist_ok=True)
    return d
