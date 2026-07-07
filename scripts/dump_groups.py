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
