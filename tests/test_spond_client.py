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
        assert kwargs["include_scheduled"] is True  # placeholder trainings (invites not sent)
        assert len(events) == 1 and events[0].id == "e1" and events[0].title == "Trening"

async def test_events_for_subgroup_handles_none():
    with patch("tnn_sync.spond_client.Spond") as MockSpond:
        MockSpond.return_value.get_events = AsyncMock(return_value=None)
        client = SpondClient("u", "p")
        assert await client.events_for_subgroup("G", "S", datetime(2026,1,1), datetime(2026,12,31)) == []

async def test_events_for_group_maps_and_passes_params_without_subgroup():
    with patch("tnn_sync.spond_client.Spond") as MockSpond:
        inst = MockSpond.return_value
        inst.get_events = AsyncMock(return_value=RAW)
        client = SpondClient("user@example.com", "pw")
        events = await client.events_for_group(
            "G1", datetime(2026, 1, 1), datetime(2026, 12, 31))
        inst.get_events.assert_awaited_once()
        kwargs = inst.get_events.await_args.kwargs
        assert kwargs["group_id"] == "G1"
        assert kwargs["include_scheduled"] is True  # placeholder trainings (invites not sent)
        assert "subgroup_id" not in kwargs
        assert len(events) == 1 and events[0].id == "e1" and events[0].title == "Trening"

async def test_events_for_group_handles_none():
    with patch("tnn_sync.spond_client.Spond") as MockSpond:
        MockSpond.return_value.get_events = AsyncMock(return_value=None)
        client = SpondClient("u", "p")
        assert await client.events_for_group("G", datetime(2026,1,1), datetime(2026,12,31)) == []
