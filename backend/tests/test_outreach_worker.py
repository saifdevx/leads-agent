from datetime import datetime, timezone
from app.outreach.worker import _can_send_now


class Repo:
    def __init__(self, count=0, last=None): self.count=count; self.last=last
    def sent_today_count(self, *args): return self.count
    def last_sent_at(self, *args): return self.last


def test_worker_allows_message_in_window_under_limit():
    message = {"timezone":"UTC","send_start_hour":9,"send_end_hour":17,"daily_limit":30,"min_interval_seconds":60,"sender_id":"s"}
    allowed, next_at = _can_send_now(message, Repo(), datetime(2026,1,1,12,0,tzinfo=timezone.utc))
    assert allowed is True
    assert next_at is None


def test_worker_defers_when_daily_limit_reached():
    message = {"timezone":"UTC","send_start_hour":9,"send_end_hour":17,"daily_limit":1,"min_interval_seconds":60,"sender_id":"s"}
    allowed, next_at = _can_send_now(message, Repo(count=1), datetime(2026,1,1,12,0,tzinfo=timezone.utc))
    assert allowed is False
    assert next_at is not None
