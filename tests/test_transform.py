from datetime import datetime
from tnn_sync.models import SpondEvent, OSLO
from tnn_sync.transform import build_activities

def _ev(id, title, y, mo, d, endday=None, match_event=False):
    start = datetime(y, mo, d, 10, 0, tzinfo=OSLO)
    end = datetime(y, mo, endday, 12, 0, tzinfo=OSLO) if endday else None
    return SpondEvent(id=id, title=title, start=start, end=end, cancelled=False, cancelled_reason=None,
                      series_id=None, match_event=match_event)

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

def _train(id, y, mo, d, h1, m1, h2, m2, cancelled=False, title="TNN16-A"):
    return SpondEvent(id=id, title=title,
                      start=datetime(y, mo, d, h1, m1, tzinfo=OSLO),
                      end=datetime(y, mo, d, h2, m2, tzinfo=OSLO),
                      cancelled=cancelled, cancelled_reason=None,
                      series_id="S1", match_event=False)

def test_build_training_pattern_collapses_and_flags_fpn():
    events = [
        _train("t1", 2026, 7, 7, 15, 50, 17, 30, title="TNN16-A"),   # Tue
        _train("t2", 2026, 7, 14, 15, 50, 17, 30, title="TNN16-A"),  # Tue (duplicate slot)
        _train("t3", 2026, 7, 9, 15, 35, 17, 0, title="TNN16-A FPN"),    # Thu
    ]
    result = build_training_pattern(events)
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
                   cancelled=True, cancelled_reason="Ferie",
                   series_id="S1", match_event=False),      # earlier Thu cancelled
    ]
    assert build_cancellations(events) == [
        {"date": "2026-07-02", "weekday": 4, "reason": "Ferie"},
        {"date": "2026-07-09", "weekday": 4},
    ]

from tnn_sync.transform import build_trainings

def test_build_trainings_per_date_sorted_with_flags():
    events = [
        _train("t2", 2026, 7, 9, 15, 35, 17, 0, title="TNN16-A FPN"),   # Thu, fpn
        _train("t1", 2026, 7, 7, 16, 0, 17, 30, title="TNN16-A"),       # Tue, earlier
        SpondEvent(id="t3", title="Trening",
                   start=datetime(2026, 7, 4, 13, 30, tzinfo=OSLO),
                   end=datetime(2026, 7, 4, 14, 30, tzinfo=OSLO),
                   cancelled=True, cancelled_reason="Ferie",
                   series_id="S1", match_event=False),                  # Sat, cancelled
    ]
    result = build_trainings(events)
    assert result == [
        {"date": "2026-07-04", "weekday": 6, "time": "13:30–14:30", "fpn": False,
         "cancelled": True, "reason": "Ferie"},
        {"date": "2026-07-07", "weekday": 2, "time": "16:00–17:30", "fpn": False,
         "cancelled": False},
        {"date": "2026-07-09", "weekday": 4, "time": "15:35–17:00", "fpn": True,
         "cancelled": False},
    ]

def test_build_trainings_cancelled_without_reason_omits_reason_key():
    events = [_train("t1", 2026, 7, 9, 15, 35, 17, 0, cancelled=True)]
    result = build_trainings(events)
    assert result == [{"date": "2026-07-09", "weekday": 4, "time": "15:35–17:00",
                       "fpn": False, "cancelled": True}]

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

def test_build_activities_stable_tiebreak_on_same_date():
    # same start date, deliberately reversed id order on input
    events = {"cup": [_ev("zzz", "B", 2026, 5, 10), _ev("aaa", "A", 2026, 5, 10)]}
    result = build_activities(events)
    assert [a["id"] for a in result] == ["aaa", "zzz"]

def test_build_cancellations_stable_tiebreak_on_same_date():
    # Two cancellations on different dates; verify the sorted output order is
    # deterministic regardless of input order (guards against relying on
    # Spond's return order, which is not guaranteed stable).
    e_a = _train("t_a", 2026, 5, 12, 18, 0, 19, 0, cancelled=True)  # Tue
    e_b = _train("t_b", 2026, 5, 14, 18, 0, 19, 0, cancelled=True)  # Thu
    result = build_cancellations([e_b, e_a])
    assert result == build_cancellations([e_a, e_b])
    assert [c["date"] for c in result] == ["2026-05-12", "2026-05-14"]

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

from tnn_sync.transform import categorize

RULES = [("cup", "cup"), ("turnering", "cup"), ("sosial", "sosialt"), ("camp", "leir"),
         ("leir", "leir"), ("møte", "dugnad"), ("dugnad", "dugnad"), ("loppe", "dugnad"),
         ("isfa", "kamp")]

def test_categorize_cup_keyword():
    e = _ev("a", "Stjerne Cup 2026", 2026, 8, 1)
    assert categorize(e, RULES, fallback="sosialt") == "cup"

def test_categorize_sosialt_keyword():
    e = _ev("b", "Sosial happening hos Eddie", 2026, 8, 1)
    assert categorize(e, RULES, fallback="sosialt") == "sosialt"

def test_categorize_leir_keyword_from_camp():
    e = _ev("c", "BEKREFTET matchcamp i Drammen...", 2026, 8, 1)
    assert categorize(e, RULES, fallback="sosialt") == "leir"

def test_categorize_dugnad_keyword_from_mote():
    e = _ev("d", "Foreldremøte TNN16-A", 2026, 8, 1)
    assert categorize(e, RULES, fallback="sosialt") == "dugnad"

def test_categorize_match_event_no_keyword_is_kamp():
    e = _ev("e", "Random title", 2026, 8, 1, match_event=True)
    assert categorize(e, RULES, fallback="sosialt") == "kamp"

def test_categorize_unknown_title_falls_back():
    e = _ev("f", "Something completely unrelated", 2026, 8, 1)
    assert categorize(e, RULES, fallback="sosialt") == "sosialt"
