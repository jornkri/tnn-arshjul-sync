# TNN Årshjul Sync-backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python sync job that logs into Spond, transforms events into `arshjul.json`, validates it, and publishes it to GitHub Pages on a 15-minute schedule.

**Architecture:** A thin async Spond client fetches events per subgroup (subgroup → category). Pure transform functions turn normalized events into the JSON contract. A robustness guard refuses to publish an empty/invalid plan so a Spond glitch never wipes the last-good file. A GitHub Actions cron runs it and deploys the JSON to Pages.

**Tech Stack:** Python 3.11+, `spond` (unofficial async Spond client), `jsonschema`, `PyYAML`, `pytest`, `pytest-asyncio`. `zoneinfo` for Europe/Oslo time conversion.

**Reference spec:** `~/dev/tnn-arshjul-app/docs/superpowers/specs/2026-07-07-tnn-arshjul-design.md` (sections 4 and 6 define the JSON contract and backend).

---

## File Structure

```
tnn-arshjul-sync/
  pyproject.toml            # package + deps + pytest config
  .gitignore
  README.md                 # setup: secrets, config, discovery, run
  config.example.yaml       # committed template
  config.yaml               # real ids, gitignored until filled
  schema.json               # JSON Schema for arshjul.json
  tnn_sync/
    __init__.py
    models.py               # SpondEvent dataclass + parse_event() + OSLO tz
    labels.py               # Norwegian weekday/month names + format_date_label()
    transform.py            # build_activities/pattern/cancellations/plan + is_publishable
    config.py               # Config dataclass + load_config()
    validate.py             # load_schema() + validate_plan()
    spond_client.py         # SpondClient async wrapper (imports spond + models)
    main.py                 # orchestration + write guard
  scripts/
    dump_groups.py          # one-off: dump group/subgroup ids for config
  tests/
    conftest.py
    fixtures/raw_event.json # captured shape of one Spond event (setup task)
    test_parse_event.py
    test_labels.py
    test_transform.py
    test_config.py
    test_validate.py
    test_spond_client.py
    test_main_guard.py
  public/
    arshjul.json            # build output, deployed to Pages
  .github/workflows/sync.yml
```

**Type contract used across tasks** (defined in Task 1, referenced everywhere):

```python
@dataclass(frozen=True)
class SpondEvent:
    id: str
    title: str
    start: datetime        # timezone-aware, Europe/Oslo
    end: datetime | None   # timezone-aware, Europe/Oslo, or None
    cancelled: bool
    cancelled_reason: str | None
```

Output JSON keys (per spec §4): `schemaVersion`, `generatedAt`, `season`, `categories`, `activities[]{id,title,category,start,end?,dateLabel}`, `trainingPattern[]{weekday,time,fpn,label}`, `cancellations[]{date,weekday,reason?}`. `weekday` is ISO (1=Mon…7=Sun).

---

## Task 0: Project scaffold

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `tnn_sync/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "tnn-arshjul-sync"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["spond>=1.0", "jsonschema>=4.0", "PyYAML>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["tnn_sync"]
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
.pytest_cache/
config.yaml
exports/
```

- [ ] **Step 3: Create empty `tnn_sync/__init__.py` and `tests/conftest.py`**

`tnn_sync/__init__.py`: empty file.
`tests/conftest.py`: empty file (rootdir marker; editable install handles imports).

- [ ] **Step 4: Create venv and install**

Run:
```bash
cd ~/dev/tnn-arshjul-sync && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
```
Expected: installs spond, jsonschema, PyYAML, pytest, pytest-asyncio without error.

- [ ] **Step 5: Verify pytest runs (no tests yet)**

Run: `. .venv/bin/activate && pytest -q`
Expected: "no tests ran" (exit 5) — confirms discovery works.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore tnn_sync/__init__.py tests/conftest.py
git commit -m "chore: scaffold tnn-arshjul-sync project"
```

---

## Task 1: `parse_event` — normalize raw Spond dict → SpondEvent

**Files:**
- Create: `tnn_sync/models.py`
- Test: `tests/test_parse_event.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_parse_event.py
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
    )

def test_parse_event_missing_end_and_cancelled_defaults():
    raw = {"id": "e2", "heading": "Cup", "startTimestamp": "2026-07-27T08:00:00Z",
           "cancelled": True, "cancelledReason": "Ferie"}
    e = parse_event(raw)
    assert e.end is None
    assert e.cancelled is True
    assert e.cancelled_reason == "Ferie"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_parse_event.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tnn_sync.models'`

- [ ] **Step 3: Write minimal implementation**

```python
# tnn_sync/models.py
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
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_parse_event.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add tnn_sync/models.py tests/test_parse_event.py
git commit -m "feat: parse raw Spond event to timezone-aware SpondEvent"
```

---

## Task 2: `labels` — Norwegian date labels

**Files:**
- Create: `tnn_sync/labels.py`
- Test: `tests/test_labels.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_labels.py
from datetime import date
from tnn_sync.labels import format_date_label, WEEKDAY_NB

def test_single_day():
    assert format_date_label(date(2026, 6, 7), None) == "7. juni"

def test_single_day_when_end_same_date():
    assert format_date_label(date(2026, 6, 7), date(2026, 6, 7)) == "7. juni"

def test_range_same_month():
    assert format_date_label(date(2026, 7, 1), date(2026, 7, 4)) == "1.–4. juli"

def test_range_across_months():
    assert format_date_label(date(2026, 7, 27), date(2026, 8, 2)) == "27. juli – 2. august"

def test_weekday_names():
    assert WEEKDAY_NB[2] == "Tirsdag" and WEEKDAY_NB[6] == "Lørdag"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_labels.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tnn_sync.labels'`

- [ ] **Step 3: Write minimal implementation**

```python
# tnn_sync/labels.py
from datetime import date

MONTH_NB = {1: "januar", 2: "februar", 3: "mars", 4: "april", 5: "mai", 6: "juni",
            7: "juli", 8: "august", 9: "september", 10: "oktober", 11: "november", 12: "desember"}
MONTH_NB_TITLE = {n: name.capitalize() for n, name in MONTH_NB.items()}
WEEKDAY_NB = {1: "Mandag", 2: "Tirsdag", 3: "Onsdag", 4: "Torsdag",
              5: "Fredag", 6: "Lørdag", 7: "Søndag"}

def format_date_label(start: date, end: date | None) -> str:
    if end is None or end == start:
        return f"{start.day}. {MONTH_NB[start.month]}"
    if start.month == end.month:
        return f"{start.day}.–{end.day}. {MONTH_NB[end.month]}"
    return f"{start.day}. {MONTH_NB[start.month]} – {end.day}. {MONTH_NB[end.month]}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_labels.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add tnn_sync/labels.py tests/test_labels.py
git commit -m "feat: Norwegian date-label and weekday/month name helpers"
```

---

## Task 3: `build_activities`

**Files:**
- Create: `tnn_sync/transform.py`
- Test: `tests/test_transform.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_transform.py
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
    # sorted by start date ascending
    assert [a["id"] for a in result] == ["c", "b", "a"]
    assert result[0] == {"id": "c", "title": "Sommerleir", "category": "leir",
                         "start": "2026-07-01", "end": "2026-07-04", "dateLabel": "1.–4. juli"}
    # single-day event has no 'end' key
    assert "end" not in result[1]
    assert result[1]["dateLabel"] == "27. juli"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_transform.py::test_build_activities_single_and_range_sorted -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tnn_sync.transform'`

- [ ] **Step 3: Write minimal implementation**

```python
# tnn_sync/transform.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_transform.py::test_build_activities_single_and_range_sorted -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tnn_sync/transform.py tests/test_transform.py
git commit -m "feat: build_activities from categorized Spond events"
```

---

## Task 4: `build_training_pattern`

**Files:**
- Modify: `tnn_sync/transform.py`
- Test: `tests/test_transform.py`

- [ ] **Step 1: Write the failing test (append)**

```python
# tests/test_transform.py (append)
from tnn_sync.transform import build_training_pattern

def _train(id, y, mo, d, h1, m1, h2, m2, cancelled=False):
    return SpondEvent(id=id, title="Trening",
                      start=datetime(y, mo, d, h1, m1, tzinfo=OSLO),
                      end=datetime(y, mo, d, h2, m2, tzinfo=OSLO),
                      cancelled=cancelled, cancelled_reason=None)

def test_build_training_pattern_collapses_and_flags_fpn():
    # two Tuesdays same slot + one Thursday; Thursday weekday(4) is fpn
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_transform.py::test_build_training_pattern_collapses_and_flags_fpn -v`
Expected: FAIL — `ImportError: cannot import name 'build_training_pattern'`

- [ ] **Step 3: Write minimal implementation (append to transform.py)**

```python
# tnn_sync/transform.py (append)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_transform.py::test_build_training_pattern_collapses_and_flags_fpn -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tnn_sync/transform.py tests/test_transform.py
git commit -m "feat: derive weekly trainingPattern from recurring events"
```

---

## Task 5: `build_cancellations`

**Files:**
- Modify: `tnn_sync/transform.py`
- Test: `tests/test_transform.py`

- [ ] **Step 1: Write the failing test (append)**

```python
# tests/test_transform.py (append)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_transform.py::test_build_cancellations_only_cancelled_sorted -v`
Expected: FAIL — `ImportError: cannot import name 'build_cancellations'`

- [ ] **Step 3: Write minimal implementation (append)**

```python
# tnn_sync/transform.py (append)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_transform.py::test_build_cancellations_only_cancelled_sorted -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tnn_sync/transform.py tests/test_transform.py
git commit -m "feat: build_cancellations from cancelled training events"
```

---

## Task 6: `build_plan` assembler + `is_publishable`

**Files:**
- Modify: `tnn_sync/transform.py`
- Test: `tests/test_transform.py`

- [ ] **Step 1: Write the failing test (append)**

```python
# tests/test_transform.py (append)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_transform.py -k "build_plan or publishable" -v`
Expected: FAIL — `ImportError: cannot import name 'build_plan'`

- [ ] **Step 3: Write minimal implementation (append)**

```python
# tnn_sync/transform.py (append)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_transform.py -v`
Expected: PASS (all transform tests)

- [ ] **Step 5: Commit**

```bash
git add tnn_sync/transform.py tests/test_transform.py
git commit -m "feat: assemble plan dict and publishability guard"
```

---

## Task 7: `schema.json` + `validate_plan`

**Files:**
- Create: `schema.json`, `tnn_sync/validate.py`
- Test: `tests/test_validate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validate.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_validate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tnn_sync.validate'`

- [ ] **Step 3: Create `schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schemaVersion", "generatedAt", "season", "categories", "activities", "trainingPattern", "cancellations"],
  "properties": {
    "schemaVersion": {"const": 1},
    "generatedAt": {"type": "string"},
    "season": {
      "type": "object",
      "required": ["year", "label", "accent"],
      "properties": {
        "year": {"type": "integer"},
        "label": {"type": "string"},
        "accent": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"}
      }
    },
    "categories": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["label", "color", "icon"],
        "properties": {
          "label": {"type": "string"},
          "color": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
          "icon": {"type": "string"}
        }
      }
    },
    "activities": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "category", "start", "dateLabel"],
        "properties": {
          "id": {"type": "string"},
          "title": {"type": "string"},
          "category": {"type": "string"},
          "start": {"type": "string", "format": "date"},
          "end": {"type": "string", "format": "date"},
          "dateLabel": {"type": "string"}
        }
      }
    },
    "trainingPattern": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["weekday", "time", "fpn", "label"],
        "properties": {
          "weekday": {"type": "integer", "minimum": 1, "maximum": 7},
          "time": {"type": "string"},
          "fpn": {"type": "boolean"},
          "label": {"type": "string"}
        }
      }
    },
    "cancellations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["date", "weekday"],
        "properties": {
          "date": {"type": "string", "format": "date"},
          "weekday": {"type": "integer", "minimum": 1, "maximum": 7},
          "reason": {"type": "string"}
        }
      }
    }
  }
}
```

- [ ] **Step 4: Write `tnn_sync/validate.py`**

```python
# tnn_sync/validate.py
import json
from pathlib import Path
from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.json"

def load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

def validate_plan(plan: dict) -> None:
    Draft202012Validator(load_schema()).validate(plan)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_validate.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add schema.json tnn_sync/validate.py tests/test_validate.py
git commit -m "feat: JSON Schema and validate_plan"
```

---

## Task 8: `config.py` — load config.yaml

**Files:**
- Create: `tnn_sync/config.py`, `config.example.yaml`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from tnn_sync.config import load_config, Config

YAML = """
group_id: "GROUP123"
season:
  year: 2026
  label: "TNN 2016-A"
  accent: "#E8112D"
categories:
  cup: {label: "Cup / turnering", color: "#FF4D4D", icon: "cup"}
activity_subgroups:
  SUBcup: cup
training_subgroup_id: "SUBtrening"
fpn_weekdays: [4]
output_path: "public/arshjul.json"
"""

def test_load_config(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(YAML, encoding="utf-8")
    cfg = load_config(p)
    assert isinstance(cfg, Config)
    assert cfg.group_id == "GROUP123"
    assert cfg.season["year"] == 2026
    assert cfg.activity_subgroups == {"SUBcup": "cup"}
    assert cfg.training_subgroup_id == "SUBtrening"
    assert cfg.fpn_weekdays == [4]
    assert cfg.categories["cup"]["icon"] == "cup"
    assert cfg.output_path == "public/arshjul.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tnn_sync.config'`

- [ ] **Step 3: Write minimal implementation**

```python
# tnn_sync/config.py
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class Config:
    group_id: str
    season: dict
    categories: dict
    activity_subgroups: dict   # {subgroup_id: category_key}
    training_subgroup_id: str
    fpn_weekdays: list[int]
    output_path: str

def load_config(path: str | Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Config(
        group_id=data["group_id"],
        season=data["season"],
        categories=data["categories"],
        activity_subgroups=data["activity_subgroups"],
        training_subgroup_id=data["training_subgroup_id"],
        fpn_weekdays=data.get("fpn_weekdays", []),
        output_path=data.get("output_path", "public/arshjul.json"),
    )
```

- [ ] **Step 4: Create `config.example.yaml` (committed template)**

```yaml
# Copy to config.yaml and fill in real Spond ids (run scripts/dump_groups.py to discover them).
group_id: "REPLACE_WITH_GROUP_ID"
season:
  year: 2026
  label: "TNN 2016-A"
  accent: "#E8112D"
# The 6 categories rendered by the app (color/icon/label live here).
categories:
  cup:     {label: "Cup / turnering", color: "#FF4D4D", icon: "cup"}
  trening: {label: "Trening",         color: "#3DA0FF", icon: "trening"}
  sosialt: {label: "Sosialt",         color: "#FFC53D", icon: "sosialt"}
  leir:    {label: "Treningsleir",    color: "#34D9A0", icon: "leir"}
  dugnad:  {label: "Dugnad",          color: "#B98BFF", icon: "dugnad"}
  kamp:    {label: "Kamp / serie",    color: "#FF8A3D", icon: "kamp"}
# Map each activity subgroup id to a category key above.
activity_subgroups:
  REPLACE_WITH_SUBGROUP_ID: cup
# The subgroup id whose events are the fixed weekly trainings.
training_subgroup_id: "REPLACE_WITH_TRAINING_SUBGROUP_ID"
# ISO weekdays (1=Mon..7=Sun) whose training is an FPN session.
fpn_weekdays: [4]
output_path: "public/arshjul.json"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tnn_sync/config.py config.example.yaml tests/test_config.py
git commit -m "feat: config loader and example config"
```

---

## Task 9: `spond_client.py` — async wrapper

**Files:**
- Create: `tnn_sync/spond_client.py`
- Test: `tests/test_spond_client.py`

- [ ] **Step 1: Write the failing test (uses AsyncMock, no network)**

```python
# tests/test_spond_client.py
from datetime import datetime
from unittest.mock import AsyncMock, patch
from tnn_sync.spond_client import SpondClient

RAW = [{"id": "e1", "heading": "Trening", "startTimestamp": "2026-07-02T13:50:00Z",
        "endTimestamp": "2026-07-02T15:30:00Z"}]

async def test_events_for_subgroup_maps_and_passes_params():
    with patch("tnn_sync.spond_client.Spond") as MockSpond:
        inst = MockSpond.return_value
        inst.get_events = AsyncMock(return_value=RAW)
        client = SpondClient("user@example.com", "pw")
        events = await client.events_for_subgroup(
            "G1", "S1", datetime(2026, 1, 1), datetime(2026, 12, 31))
        inst.get_events.assert_awaited_once()
        kwargs = inst.get_events.await_args.kwargs
        assert kwargs["group_id"] == "G1" and kwargs["subgroup_id"] == "S1"
        assert len(events) == 1 and events[0].id == "e1" and events[0].title == "Trening"

async def test_events_for_subgroup_handles_none():
    with patch("tnn_sync.spond_client.Spond") as MockSpond:
        MockSpond.return_value.get_events = AsyncMock(return_value=None)
        client = SpondClient("u", "p")
        assert await client.events_for_subgroup("G", "S", datetime(2026,1,1), datetime(2026,12,31)) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_spond_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tnn_sync.spond_client'`

- [ ] **Step 3: Write minimal implementation**

```python
# tnn_sync/spond_client.py
from datetime import datetime
from spond.spond import Spond
from tnn_sync.models import SpondEvent, parse_event

class SpondClient:
    def __init__(self, username: str, password: str):
        self._s = Spond(username=username, password=password)

    async def events_for_subgroup(self, group_id: str, subgroup_id: str,
                                  min_start: datetime, max_start: datetime) -> list[SpondEvent]:
        raw = await self._s.get_events(
            group_id=group_id, subgroup_id=subgroup_id,
            min_start=min_start, max_start=max_start, max_events=500,
        )
        return [parse_event(e) for e in (raw or [])]

    async def close(self) -> None:
        await self._s.clientsession.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_spond_client.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add tnn_sync/spond_client.py tests/test_spond_client.py
git commit -m "feat: async SpondClient wrapper with event mapping"
```

---

## Task 10: `main.py` — orchestration + write guard

**Files:**
- Create: `tnn_sync/main.py`
- Test: `tests/test_main_guard.py`

- [ ] **Step 1: Write the failing test (guard logic only — no network)**

```python
# tests/test_main_guard.py
import json
import pytest
from tnn_sync.main import write_plan_guarded

VALID = {
    "schemaVersion": 1, "generatedAt": "2026-07-07T12:15:00Z",
    "season": {"year": 2026, "label": "TNN 2016-A", "accent": "#E8112D"},
    "categories": {"cup": {"label": "Cup", "color": "#FF4D4D", "icon": "cup"}},
    "activities": [{"id": "b", "title": "Norway Cup", "category": "cup",
                    "start": "2026-07-27", "dateLabel": "27. juli"}],
    "trainingPattern": [], "cancellations": [],
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
    # previous file untouched
    assert json.loads(out.read_text(encoding="utf-8")) == {"previous": True}

def test_refuses_invalid_plan(tmp_path):
    out = tmp_path / "public" / "arshjul.json"
    invalid = {k: v for k, v in VALID.items() if k != "season"}
    with pytest.raises(SystemExit):
        write_plan_guarded(invalid, out)
    assert not out.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main_guard.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tnn_sync.main'`

- [ ] **Step 3: Write minimal implementation**

```python
# tnn_sync/main.py
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from tnn_sync.config import Config, load_config
from tnn_sync.spond_client import SpondClient
from tnn_sync.transform import (
    build_activities, build_training_pattern, build_cancellations,
    build_plan, is_publishable,
)
from tnn_sync.validate import validate_plan

def write_plan_guarded(plan: dict, out_path: Path) -> None:
    """Validate + publishability check, then write. Exit non-zero (keeping any
    existing file) if the plan is empty or invalid, so a Spond glitch never
    wipes the last-good published file."""
    if not is_publishable(plan):
        print("Refusing to publish: plan has no activities or training.", file=sys.stderr)
        raise SystemExit(1)
    try:
        validate_plan(plan)
    except Exception as exc:  # jsonschema.ValidationError
        print(f"Refusing to publish: schema validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(f"Wrote {out_path}")

async def _collect(client: SpondClient, cfg: Config, min_start: datetime, max_start: datetime):
    events_by_category: dict[str, list] = {}
    for subgroup_id, category in cfg.activity_subgroups.items():
        evs = await client.events_for_subgroup(cfg.group_id, subgroup_id, min_start, max_start)
        events_by_category.setdefault(category, []).extend(evs)
    training = await client.events_for_subgroup(
        cfg.group_id, cfg.training_subgroup_id, min_start, max_start)
    return events_by_category, training

async def _run_async(cfg: Config) -> dict:
    username = os.environ["SPOND_USERNAME"]
    password = os.environ["SPOND_PASSWORD"]
    year = cfg.season["year"]
    min_start = datetime(year, 1, 1)
    max_start = datetime(year, 12, 31, 23, 59)
    client = SpondClient(username, password)
    try:
        events_by_category, training = await _collect(client, cfg, min_start, max_start)
    finally:
        await client.close()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return build_plan(
        season=cfg.season,
        categories=cfg.categories,
        activities=build_activities(events_by_category),
        training_pattern=build_training_pattern(training, cfg.fpn_weekdays),
        cancellations=build_cancellations(training),
        generated_at=generated_at,
    )

def main() -> None:
    cfg = load_config("config.yaml")
    plan = asyncio.run(_run_async(cfg))
    write_plan_guarded(plan, Path(cfg.output_path))

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main_guard.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add tnn_sync/main.py tests/test_main_guard.py
git commit -m "feat: orchestration entrypoint with publish guard"
```

---

## Task 11: `scripts/dump_groups.py` — discovery helper

**Files:**
- Create: `scripts/dump_groups.py`

No automated test (one-off operational utility that hits the network).

- [ ] **Step 1: Write the script**

```python
# scripts/dump_groups.py
"""Print group ids/names and their subgroup ids/names, to fill in config.yaml.
Run:  SPOND_USERNAME=... SPOND_PASSWORD=... python scripts/dump_groups.py
"""
import asyncio
import os
from spond.spond import Spond

async def main() -> None:
    s = Spond(username=os.environ["SPOND_USERNAME"], password=os.environ["SPOND_PASSWORD"])
    try:
        groups = await s.get_groups() or []
        for g in groups:
            print(f'GROUP  id={g["id"]!r}  name={g["name"]!r}')
            for sub in g.get("subGroups", []):
                print(f'   SUBGROUP  id={sub["id"]!r}  name={sub["name"]!r}')
    finally:
        await s.clientsession.close()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
git add scripts/dump_groups.py
git commit -m "chore: add Spond group/subgroup discovery script"
```

---

## Task 12: GitHub Actions workflow + README

**Files:**
- Create: `.github/workflows/sync.yml`, `README.md`

- [ ] **Step 1: Write `.github/workflows/sync.yml`**

```yaml
name: Sync Spond → arshjul.json
on:
  schedule:
    - cron: "*/15 * * * *"   # every 15 min (GitHub may delay under load)
  workflow_dispatch: {}       # manual run button

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e .
      - name: Run sync
        env:
          SPOND_USERNAME: ${{ secrets.SPOND_USERNAME }}
          SPOND_PASSWORD: ${{ secrets.SPOND_PASSWORD }}
        run: python -m tnn_sync.main
      - uses: actions/upload-pages-artifact@v3
        with:
          path: public
      - uses: actions/deploy-pages@v4
```

Note: `config.yaml` must be committed (it holds non-secret ids) for CI to read it — it is gitignored by default in Task 0, so in the setup steps below it is force-added.

- [ ] **Step 2: Write `README.md`**

````markdown
# TNN Årshjul — Sync backend

Fetches the season plan from Spond and publishes `public/arshjul.json` to GitHub
Pages every 15 minutes. The iOS app reads that JSON. See
`docs/superpowers/plans/2026-07-07-tnn-arshjul-sync.md` and the design spec in the
app repo.

## One-time setup

1. **Install:** `python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"`
2. **Discover Spond ids:**
   ```bash
   SPOND_USERNAME='you@example.com' SPOND_PASSWORD='...' python scripts/dump_groups.py
   ```
3. **Configure:** `cp config.example.yaml config.yaml`, fill in `group_id`,
   `activity_subgroups` (subgroup id → category), `training_subgroup_id`,
   `fpn_weekdays`, and `season`. Commit it (ids are not secret):
   `git add -f config.yaml && git commit -m "chore: real Spond config"`.
4. **GitHub secrets:** in repo Settings → Secrets and variables → Actions, add
   `SPOND_USERNAME` and `SPOND_PASSWORD` (a Spond account that is a member of the group).
5. **Enable Pages:** Settings → Pages → Source = "GitHub Actions".

## Local run

```bash
SPOND_USERNAME='...' SPOND_PASSWORD='...' python -m tnn_sync.main
cat public/arshjul.json
```

## Tests

```bash
pytest -q
```
````

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/sync.yml README.md
git commit -m "ci: add scheduled Spond sync workflow and README"
```

---

## Task 13: End-to-end verification (manual, at setup)

**Not a code task — run once the operational values from spec §10 are available.**

- [ ] **Step 1:** Complete README setup steps 1–3 (real `config.yaml`).
- [ ] **Step 2:** Capture a real event for the fixture:
  add a throwaway script or REPL call to `client.events_for_subgroup(...)` /
  `s.get_events(...)`, save one raw event dict to `tests/fixtures/raw_event.json`,
  and confirm `parse_event` handles it (extend `test_parse_event.py` with a
  fixture-based test if any real key differs from Task 1's assumptions —
  especially `cancelled` / `cancelledReason`).
- [ ] **Step 3:** Run `python -m tnn_sync.main` locally and inspect
  `public/arshjul.json` — verify activities land in the right months, training
  times are Oslo-local, and cancellations look right.
- [ ] **Step 4:** Push, then trigger the workflow via **Run workflow**
  (workflow_dispatch) and confirm Pages serves the JSON at
  `https://<github-username>.github.io/tnn-arshjul-sync/arshjul.json`.

---

## Self-review notes

- **Spec coverage:** JSON contract (§4) → Tasks 3–7; subgroup→category (§3) →
  Tasks 8+10; timezone-correct training times (§7) → Task 1; robustness "never
  publish empty/invalid" (§6) → Tasks 6, 10; idempotent stable JSON (§6) →
  `sort_keys=True` + sorted lists in Tasks 3/5/10; cron `*/15` + workflow_dispatch
  (§3) → Task 12; discovery of ids (§10) → Task 11.
- **Deferred-to-setup (not placeholders):** real Spond ids, credentials, the
  captured raw-event fixture, and GitHub username live in spec §10 and README —
  they are operational inputs, exercised in Task 13.
- **Type consistency:** `SpondEvent` fields, `build_*` signatures, config keys,
  and JSON keys match across Tasks 1–10 and the schema in Task 7.
- **Known assumption to confirm against real data (Task 13):** raw keys
  `cancelled` / `cancelledReason`. `parse_event` defaults them safely, so a
  mismatch degrades gracefully (no cancellations) rather than crashing.
