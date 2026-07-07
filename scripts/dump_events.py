"""Inspect events in a Spond group to design the category mapping.
Run:  SPOND_USERNAME=... SPOND_PASSWORD=... python scripts/dump_events.py <group_id>
Prints a non-personal summary (heading, start/end, cancelled, recurrence hints)
plus the raw key list of the first event so we can see the real schema.
"""
import asyncio
import os
import sys
from datetime import datetime
from spond.spond import Spond


async def main() -> None:
    group_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GROUP_ID", "")
    s = Spond(username=os.environ["SPOND_USERNAME"], password=os.environ["SPOND_PASSWORD"])
    try:
        events = await s.get_events(
            group_id=group_id,
            min_start=datetime(2026, 1, 1),
            max_start=datetime(2027, 1, 1),
            max_events=300,
        ) or []
        print(f"{len(events)} events in group {group_id}\n")
        if events:
            print("RAW KEYS of first event:", sorted(events[0].keys()), "\n")
        for e in events:
            heading = e.get("heading", "?")
            start = e.get("startTimestamp", "?")
            end = e.get("endTimestamp", "")
            cancelled = e.get("cancelled", False)
            # recurrence hints — print any key mentioning recurrence/series/repeat
            rec = {k: e[k] for k in e if any(t in k.lower() for t in ("recur", "series", "repeat"))}
            print(f"- {start}  {heading!r}  end={end}  cancelled={cancelled}  rec={rec}")
    finally:
        await s.clientsession.close()


if __name__ == "__main__":
    asyncio.run(main())
