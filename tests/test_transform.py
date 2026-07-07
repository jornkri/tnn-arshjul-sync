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
