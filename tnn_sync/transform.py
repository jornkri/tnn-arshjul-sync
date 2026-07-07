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

def _slot_time(e: SpondEvent) -> str:
    return f"{e.start:%H:%M}–{e.end:%H:%M}"

def build_training_pattern(events: list[SpondEvent], fpn_weekdays: list[int]) -> list[dict]:
    seen: dict[tuple[int, str], dict] = {}
    for e in events:
        weekday = e.start.isoweekday()
        time = _slot_time(e)
        key = (weekday, time)
        if key not in seen:
            seen[key] = {
                "weekday": weekday,
                "time": time,
                "fpn": weekday in fpn_weekdays,
                "label": WEEKDAY_NB[weekday],
            }
    return sorted(seen.values(), key=lambda s: (s["weekday"], s["time"]))

def build_cancellations(events: list[SpondEvent]) -> list[dict]:
    out = []
    for e in events:
        if not e.cancelled:
            continue
        item = {"date": e.start.date().isoformat(), "weekday": e.start.isoweekday()}
        if e.cancelled_reason:
            item["reason"] = e.cancelled_reason
        out.append(item)
    out.sort(key=lambda c: c["date"])
    return out

def build_plan(season: dict, categories: dict, activities: list[dict],
               training_pattern: list[dict], cancellations: list[dict],
               generated_at: str) -> dict:
    return {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "season": season,
        "categories": categories,
        "activities": activities,
        "trainingPattern": training_pattern,
        "cancellations": cancellations,
    }

def is_publishable(plan: dict) -> bool:
    return bool(plan.get("activities") or plan.get("trainingPattern"))
