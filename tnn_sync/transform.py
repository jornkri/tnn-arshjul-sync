from collections import Counter, defaultdict

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
    out.sort(key=lambda a: (a["start"], a["id"]))
    return out

def _slot_time(e: SpondEvent) -> str:
    return f"{e.start:%H:%M}–{e.end:%H:%M}"

def build_training_pattern(events: list[SpondEvent]) -> list[dict]:
    by_weekday: dict[int, list[SpondEvent]] = defaultdict(list)
    for e in events:
        by_weekday[e.start.isoweekday()].append(e)
    out = []
    for weekday, evs in by_weekday.items():
        time = Counter(_slot_time(e) for e in evs).most_common(1)[0][0]
        fpn = any("fpn" in e.title.lower() for e in evs)
        out.append({"weekday": weekday, "time": time, "fpn": fpn, "label": WEEKDAY_NB[weekday]})
    return sorted(out, key=lambda s: s["weekday"])

def build_trainings(events: list[SpondEvent]) -> list[dict]:
    """Per-date training sessions (the actual recurring-event occurrences,
    including scheduled placeholders). One entry per session, flagged cancelled."""
    out = []
    for e in events:
        item = {
            "date": e.start.date().isoformat(),
            "weekday": e.start.isoweekday(),
            "time": _slot_time(e),
            "fpn": "fpn" in e.title.lower(),
            "cancelled": e.cancelled,
        }
        if e.cancelled and e.cancelled_reason:
            item["reason"] = e.cancelled_reason
        out.append(item)
    out.sort(key=lambda t: (t["date"], t["weekday"]))
    return out

def categorize(event: SpondEvent, rules: list[tuple[str, str]], fallback: str) -> str:
    title = event.title.lower()
    for keyword, category in rules:
        if keyword in title:
            return category
    if event.match_event:
        return "kamp"
    return fallback

def build_cancellations(events: list[SpondEvent]) -> list[dict]:
    out = []
    for e in events:
        if not e.cancelled:
            continue
        item = {"date": e.start.date().isoformat(), "weekday": e.start.isoweekday()}
        if e.cancelled_reason:
            item["reason"] = e.cancelled_reason
        out.append(item)
    out.sort(key=lambda c: (c["date"], c["weekday"]))
    return out

def build_plan(season: dict, categories: dict, activities: list[dict],
               training_pattern: list[dict], cancellations: list[dict],
               generated_at: str, trainings: list[dict] | None = None) -> dict:
    return {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "season": season,
        "categories": categories,
        "activities": activities,
        "trainingPattern": training_pattern,
        "trainings": trainings or [],
        "cancellations": cancellations,
    }

def is_publishable(plan: dict) -> bool:
    return bool(plan.get("activities") or plan.get("trainingPattern"))
