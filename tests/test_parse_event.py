from datetime import datetime
from zoneinfo import ZoneInfo
from tnn_sync.models import parse_event, SpondEvent

OSLO = ZoneInfo("Europe/Oslo")

def test_parse_event_converts_utc_to_oslo():
    raw = {
        "id": "evt1",
        "heading": "Trening",
        "startTimestamp": "2026-07-02T13:50:00Z",  # 13:50 UTC = 15:50 Oslo (summer)
        "endTimestamp": "2026-07-02T15:30:00Z",
    }
    e = parse_event(raw)
    assert e == SpondEvent(
        id="evt1", title="Trening",
        start=datetime(2026, 7, 2, 15, 50, tzinfo=OSLO),
        end=datetime(2026, 7, 2, 17, 30, tzinfo=OSLO),
        cancelled=False, cancelled_reason=None,
        series_id=None, match_event=False,
    )

def test_parse_event_missing_end_and_cancelled_defaults():
    raw = {"id": "e2", "heading": "Cup", "startTimestamp": "2026-07-27T08:00:00Z",
           "cancelled": True, "cancelledReason": "Ferie"}
    e = parse_event(raw)
    assert e.end is None
    assert e.cancelled is True
    assert e.cancelled_reason == "Ferie"

def test_parse_event_series_and_match_fields():
    raw = {
        "id": "e3", "heading": "TNN16-A", "startTimestamp": "2026-07-07T15:50:00Z",
        "seriesId": "S1", "matchEvent": True,
    }
    e = parse_event(raw)
    assert e.series_id == "S1"
    assert e.match_event is True
