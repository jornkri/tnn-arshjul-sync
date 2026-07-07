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

    async def events_for_group(self, group_id: str,
                               min_start: datetime, max_start: datetime) -> list[SpondEvent]:
        raw = await self._s.get_events(
            group_id=group_id,
            min_start=min_start, max_start=max_start, max_events=500,
        )
        return [parse_event(e) for e in (raw or [])]

    async def close(self) -> None:
        await self._s.clientsession.close()
