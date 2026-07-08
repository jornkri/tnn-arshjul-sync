import json
import pytest
from tnn_sync.main import write_plan_guarded

VALID = {
    "schemaVersion": 1, "generatedAt": "2026-07-07T12:15:00Z",
    "season": {"year": 2026, "label": "TNN 2016-A", "accent": "#E8112D"},
    "categories": {"cup": {"label": "Cup", "color": "#FF4D4D", "icon": "cup"}},
    "activities": [{"id": "b", "title": "Norway Cup", "category": "cup",
                    "start": "2026-07-27", "dateLabel": "27. juli"}],
    "trainingPattern": [], "trainings": [], "cancellations": [],
}

def test_writes_valid_plan(tmp_path):
    out = tmp_path / "public" / "arshjul.json"
    write_plan_guarded(VALID, out)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["activities"][0]["id"] == "b"

def test_refuses_empty_plan_and_keeps_previous(tmp_path):
    out = tmp_path / "public" / "arshjul.json"
    out.parent.mkdir(parents=True)
    out.write_text('{"previous": true}', encoding="utf-8")
    empty = {**VALID, "activities": [], "trainingPattern": []}
    with pytest.raises(SystemExit):
        write_plan_guarded(empty, out)
    assert json.loads(out.read_text(encoding="utf-8")) == {"previous": True}

def test_refuses_invalid_plan(tmp_path):
    out = tmp_path / "public" / "arshjul.json"
    invalid = {k: v for k, v in VALID.items() if k != "season"}
    with pytest.raises(SystemExit):
        write_plan_guarded(invalid, out)
    assert not out.exists()
