import csv
import io
import json

import auth
from app import mcp
from utils import export_dir, serialize, today


@mcp.tool()
def get_activities(limit: int = 20) -> str:
    """Return the most recent activities."""
    return serialize(auth.get_client().get_activities(0, limit))


@mcp.tool()
def get_activities_by_date(start_date: str, end_date: str | None = None) -> str:
    """Return activities between start_date and end_date (YYYY-MM-DD). End defaults to today."""
    return serialize(auth.get_client().get_activities_by_date(start_date, end_date or today()))


@mcp.tool()
def get_activity_details(activity_id: str) -> str:
    """Return full details for a single activity by its ID."""
    return serialize(auth.get_client().get_activity_details(activity_id))


@mcp.tool()
def export_activity(activity_id: str, fmt: str = "gpx") -> str:
    """
    Export a single activity file. fmt options: gpx, tcx, fit, csv.
    Returns the file path where the export was saved.
    """
    fmt = fmt.lower()
    client = auth.get_client()

    fmt_map = {
        "gpx": (client.ActivityDownloadFormat.GPX, "gpx"),
        "tcx": (client.ActivityDownloadFormat.TCX, "tcx"),
        "fit": (client.ActivityDownloadFormat.ORIGINAL, "zip"),
        "csv": (client.ActivityDownloadFormat.CSV, "csv"),
    }

    if fmt not in fmt_map:
        return json.dumps({"error": f"Unknown format: {fmt}. Use gpx, tcx, fit, or csv."})

    dl_fmt, ext = fmt_map[fmt]
    data = client.download_activity(activity_id, dl_fmt=dl_fmt)
    out_path = export_dir() / f"{activity_id}.{ext}"
    out_path.write_bytes(data)
    return serialize({"path": str(out_path), "bytes": len(data)})


@mcp.tool()
def export_activities_csv(start_date: str, end_date: str | None = None) -> str:
    """Export a summary CSV of activities between start_date and end_date."""
    end = end_date or today()
    activities = auth.get_client().get_activities_by_date(start_date, end)

    if not activities:
        return json.dumps({"message": "No activities found for the given range."})

    keys = list(activities[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(activities)

    out_path = export_dir() / f"activities_{start_date}_{end}.csv"
    out_path.write_text(buf.getvalue(), encoding="utf-8")
    return serialize({"path": str(out_path), "rows": len(activities)})
