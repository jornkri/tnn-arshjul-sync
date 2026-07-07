from datetime import datetime
from tnn_sync.models import SpondEvent, OSLO
from tnn_sync.transform import build_activities

def _ev(id, title, y, mo, d, endday=None):
    start = datetime(y, mo, d, 10, 0, tzinfo=OSLO)
    end = datetime(y, mo, endday, 12, 0, tzinfo=OSLO) if endday else None
    return SpondEvent(id=id, title=title, start=start, end=end, cancelled=False, cancelled_reason=None)

def test_build_activities_single_and_range_sorted():
    events = {
        "cup": [_ev("b", "Norway Cup", 2026, 7, 27, endday=None),
                _ev("a", "Julecup", 2026, 12, 13)],
        "leir": [_ev("c", "Sommerleir", 2026, 7, 1, endday=4)],
    }
    result = build_activities(events)
    assert [a["id"] for a in result] == ["c", "b", "a"]
    assert result[0] == {"id": "c", "title": "Sommerleir", "category": "leir",
                         "start": "2026-07-01", "end": "2026-07-04", "dateLabel": "1.–4. juli"}
    assert "end" not in result[1]
    assert result[1]["dateLabel"] == "27. juli"

from tnn_sync.transform import build_training_pattern

def _train(id, y, mo, d, h1, m1, h2, m2, cancelled=False):
    return SpondEvent(id=id, title="Trening",
                      start=datetime(y, mo, d, h1, m1, tzinfo=OSLO),
                      end=datetime(y, mo, d, h2, m2, tzinfo=OSLO),
                      cancelled=cancelled, cancelled_reason=None)

def test_build_training_pattern_collapses_and_flags_fpn():
    events = [
        _train("t1", 2026, 7, 7, 15, 50, 17, 30),   # Tue
        _train("t2", 2026, 7, 14, 15, 50, 17, 30),  # Tue (duplicate slot)
        _train("t3", 2026, 7, 9, 15, 35, 17, 0),    # Thu
    ]
    result = build_training_pattern(events, fpn_weekdays=[4])
    assert result == [
        {"weekday": 2, "time": "15:50–17:30", "fpn": False, "label": "Tirsdag"},
        {"weekday": 4, "time": "15:35–17:00", "fpn": True, "label": "Torsdag"},
    ]

from tnn_sync.transform import build_cancellations

def test_build_cancellations_only_cancelled_sorted():
    events = [
        _train("t1", 2026, 7, 7, 15, 50, 17, 30),                 # not cancelled
        _train("t3", 2026, 7, 9, 15, 35, 17, 0, cancelled=True),  # Thu cancelled
        SpondEvent(id="t4", title="Trening",
                   start=datetime(2026, 7, 2, 15, 50, tzinfo=OSLO),
                   end=datetime(2026, 7, 2, 17, 30, tzinfo=OSLO),
                   cancelled=True, cancelled_reason="Ferie"),      # earlier Thu cancelled
    ]
    assert build_cancellations(events) == [
        {"date": "2026-07-02", "weekday": 4, "reason": "Ferie"},
        {"date": "2026-07-09", "weekday": 4},
    ]

from tnn_sync.transform import build_plan, is_publishable

SEASON = {"year": 2026, "label": "TNN 2016-A", "accent": "#E8112D"}
CATS = {"cup": {"label": "Cup / turnering", "color": "#FF4D4D", "icon": "cup"}}

def test_build_plan_shape():
    activities = [_ev("b", "Norway Cup", 2026, 7, 27)]
    plan = build_plan(
        season=SEASON, categories=CATS,
        activities=build_activities({"cup": activities}),
        training_pattern=[], cancellations=[],
        generated_at="2026-07-07T12:15:00Z",
    )
    assert plan["schemaVersion"] == 1
    assert plan["generatedAt"] == "2026-07-07T12:15:00Z"
    assert plan["season"] == SEASON
    assert plan["categories"] == CATS
    assert plan["activities"][0]["title"] == "Norway Cup"
    assert plan["trainingPattern"] == [] and plan["cancellations"] == []

def test_is_publishable():
    empty = build_plan(SEASON, CATS, [], [], [], "2026-07-07T12:15:00Z")
    assert is_publishable(empty) is False
    with_acts = build_plan(SEASON, CATS,
                           build_activities({"cup": [_ev("b", "Cup", 2026, 7, 27)]}),
                           [], [], "2026-07-07T12:15:00Z")
    assert is_publishable(with_acts) is True
    only_training = build_plan(SEASON, CATS, [],
                               [{"weekday": 2, "time": "15:50–17:30", "fpn": False, "label": "Tirsdag"}],
                               [], "2026-07-07T12:15:00Z")
    assert is_publishable(only_training) is True
