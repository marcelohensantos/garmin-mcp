import json

from tools.plans import save_plan


def test_save_plan_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.plans._DATA_DIR", tmp_path)
    plan = {"week_start": "2026-05-11", "focus": "threshold"}
    result = json.loads(save_plan("running_plan.json", json.dumps(plan)))
    assert "saved" in result
    saved = tmp_path / "running_plan.json"
    assert saved.exists()
    assert json.loads(saved.read_text())["focus"] == "threshold"


def test_save_plan_overwrites_existing(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.plans._DATA_DIR", tmp_path)
    save_plan("running_plan.json", json.dumps({"v": 1}))
    save_plan("running_plan.json", json.dumps({"v": 2}))
    saved = tmp_path / "running_plan.json"
    assert json.loads(saved.read_text())["v"] == 2


def test_save_plan_invalid_json(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.plans._DATA_DIR", tmp_path)
    result = json.loads(save_plan("running_plan.json", "not json"))
    assert "error" in result


def test_save_plan_preserves_unicode(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.plans._DATA_DIR", tmp_path)
    plan = {"name": "Natação S1 — Drills"}
    save_plan("swimming_plan.json", json.dumps(plan))
    saved = tmp_path / "swimming_plan.json"
    assert "Natação" in saved.read_text(encoding="utf-8")
