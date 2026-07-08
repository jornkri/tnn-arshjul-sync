import pytest
from jsonschema.exceptions import ValidationError
from tnn_sync.validate import validate_plan

VALID = {
    "schemaVersion": 1, "generatedAt": "2026-07-07T12:15:00Z",
    "season": {"year": 2026, "label": "TNN 2016-A", "accent": "#E8112D"},
    "categories": {"cup": {"label": "Cup", "color": "#FF4D4D", "icon": "cup"}},
    "activities": [{"id": "b", "title": "Norway Cup", "category": "cup",
                    "start": "2026-07-27", "dateLabel": "27. juli"}],
    "trainingPattern": [{"weekday": 2, "time": "15:50–17:30", "fpn": False, "label": "Tirsdag"}],
    "trainings": [{"date": "2026-07-07", "weekday": 2, "time": "15:50–17:30",
                   "fpn": False, "cancelled": False}],
    "cancellations": [{"date": "2026-07-09", "weekday": 4}],
}

def test_valid_plan_passes():
    validate_plan(VALID)  # must not raise

def test_missing_required_field_fails():
    bad = {k: v for k, v in VALID.items() if k != "season"}
    with pytest.raises(ValidationError):
        validate_plan(bad)

def test_bad_weekday_fails():
    bad = {**VALID, "trainingPattern": [{"weekday": 8, "time": "x", "fpn": False, "label": "?"}]}
    with pytest.raises(ValidationError):
        validate_plan(bad)
