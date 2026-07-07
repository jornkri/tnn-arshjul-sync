from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

OSLO = ZoneInfo("Europe/Oslo")

@dataclass(frozen=True)
class SpondEvent:
    id: str
    title: str
    start: datetime
    end: datetime | None
    cancelled: bool
    cancelled_reason: str | None
    series_id: str | None
    match_event: bool

def _to_oslo(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(OSLO)

def parse_event(raw: dict) -> SpondEvent:
    end_raw = raw.get("endTimestamp")
    return SpondEvent(
        id=raw["id"],
        title=raw["heading"],
        start=_to_oslo(raw["startTimestamp"]),
        end=_to_oslo(end_raw) if end_raw else None,
        cancelled=bool(raw.get("cancelled", False)),
        cancelled_reason=raw.get("cancelledReason"),
        series_id=raw.get("seriesId"),
        match_event=bool(raw.get("matchEvent", False)),
    )
