from tnn_sync.models import SpondEvent
from tnn_sync.labels import format_date_label, WEEKDAY_NB

def build_activities(events_by_category: dict[str, list[SpondEvent]]) -> list[dict]:
    out = []
    for category, events in events_by_category.items():
        for e in events:
            start_d = e.start.date()
            end_d = e.end.date() if e.end else None
            item = {
                "id": e.id,
                "title": e.title,
                "category": category,
                "start": start_d.isoformat(),
                "dateLabel": format_date_label(start_d, end_d),
            }
            if end_d and end_d != start_d:
                item["end"] = end_d.isoformat()
            out.append(item)
    out.sort(key=lambda a: a["start"])
    return out
