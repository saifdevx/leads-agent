from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import outreach


def test_quick_send_rate_limit_blocks_rapid_fire(monkeypatch):
    monkeypatch.setattr(outreach, "get_settings", lambda: SimpleNamespace(quick_send_per_minute=2))
    outreach._quick_send_events.clear()

    outreach._check_quick_send_rate("user-1")
    outreach._check_quick_send_rate("user-1")

    with pytest.raises(HTTPException) as exc:
        outreach._check_quick_send_rate("user-1")

    assert exc.value.status_code == 429
    outreach._quick_send_events.clear()
