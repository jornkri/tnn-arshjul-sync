import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from collections import defaultdict

from tnn_sync.config import Config, load_config
from tnn_sync.spond_client import SpondClient
from tnn_sync.transform import (
    build_activities, build_training_pattern, build_trainings, build_cancellations,
    build_plan, is_publishable, categorize,
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
    events = await client.events_for_group(cfg.group_id, min_start, max_start)
    recurring = [e for e in events if e.series_id]
    oneoff = [e for e in events if not e.series_id]
    return recurring, oneoff

async def _run_async(cfg: Config) -> dict:
    username = os.environ["SPOND_USERNAME"]
    password = os.environ["SPOND_PASSWORD"]
    year = cfg.season["year"]
    min_start = datetime(year, 1, 1)
    max_start = datetime(year + 1, 1, 1)
    client = SpondClient(username, password)
    try:
        recurring, oneoff = await _collect(client, cfg, min_start, max_start)
    finally:
        await client.close()
    by_cat: dict[str, list] = defaultdict(list)
    rules = [tuple(r) for r in cfg.category_rules]
    ignore = set(cfg.ignore_activity_titles)
    for e in oneoff:
        if e.title.strip().lower() in ignore:
            continue
        by_cat[categorize(e, rules, cfg.fallback_category)].append(e)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return build_plan(
        season=cfg.season,
        categories=cfg.categories,
        activities=build_activities(dict(by_cat)),
        training_pattern=build_training_pattern(recurring),
        trainings=build_trainings(recurring),
        cancellations=build_cancellations(recurring),
        generated_at=generated_at,
    )

def main() -> None:
    cfg = load_config("config.yaml")
    plan = asyncio.run(_run_async(cfg))
    write_plan_guarded(plan, Path(cfg.output_path))

if __name__ == "__main__":
    main()
