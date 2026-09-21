from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import get_settings
from app.outreach.dependencies import get_outreach_repository
from app.outreach.gmail import GmailError, refresh_access_token, send_message as send_gmail_message
from app.outreach.hostinger import HostingerMailError, send_message as send_hostinger_message
from app.outreach.sending import send_with_sender


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _zone(name: str):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return timezone.utc


def _next_window_start(now_utc: datetime, timezone_name: str, start_hour: int) -> datetime:
    zone = _zone(timezone_name)
    local = now_utc.astimezone(zone)
    candidate = local.replace(hour=start_hour % 24, minute=0, second=0, microsecond=0)
    if candidate <= local:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc)


def _day_bounds(now_utc: datetime, timezone_name: str) -> tuple[str, str]:
    zone = _zone(timezone_name)
    local = now_utc.astimezone(zone)
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc).isoformat(), end_local.astimezone(timezone.utc).isoformat()


def _can_send_now(message: dict, repository, now_utc: datetime) -> tuple[bool, datetime | None]:
    zone = _zone(str(message.get("timezone") or "UTC"))
    local = now_utc.astimezone(zone)
    start_raw = message.get("send_start_hour")
    end_raw = message.get("send_end_hour")
    start = int(9 if start_raw is None else start_raw)
    end = int(17 if end_raw is None else end_raw)
    in_window = start <= local.hour < end if end > start else (local.hour >= start or local.hour < end)
    if not in_window:
        return False, _next_window_start(now_utc, str(message.get("timezone") or "UTC"), start)

    day_start, day_end = _day_bounds(now_utc, str(message.get("timezone") or "UTC"))
    if repository.sent_today_count(message["sender_id"], day_start, day_end) >= int(message.get("daily_limit") or 30):
        return False, _next_window_start(now_utc, str(message.get("timezone") or "UTC"), start)

    last = _parse_iso(repository.last_sent_at(message["sender_id"]))
    min_interval = int(message.get("min_interval_seconds") or 30)
    if last and (now_utc - last.astimezone(timezone.utc)).total_seconds() < min_interval:
        return False, last.astimezone(timezone.utc) + timedelta(seconds=min_interval)
    return True, None


def _ensure_access_token(repository, user_id: str, sender_id: str, credentials: dict) -> dict:
    settings = get_settings()
    expires_at = _parse_iso(credentials.get("expires_at"))
    if credentials.get("access_token") and expires_at and expires_at > datetime.now(timezone.utc) + timedelta(seconds=30):
        return credentials
    refresh_token = credentials.get("refresh_token")
    if not refresh_token:
        raise GmailError("Reconnect this Gmail sender to restore offline access.")
    refreshed = refresh_access_token(
        client_id=settings.gmail_oauth_client_id,
        client_secret=settings.gmail_oauth_client_secret,
        refresh_token=refresh_token,
    )
    merged = {**credentials, **refreshed, "refresh_token": refresh_token}
    repository.update_sender_credentials(user_id, sender_id, merged)
    return merged


def process_once() -> int:
    repository = get_outreach_repository()
    processed = 0
    now_utc = datetime.now(timezone.utc)
    for message in repository.due_messages(limit=10):
        allowed, next_time = _can_send_now(message, repository, now_utc)
        if not allowed:
            repository.requeue(message["id"], (next_time or now_utc + timedelta(minutes=5)).isoformat())
            continue
        if not repository.claim_message(message["id"]):
            continue
        try:
            provider_id = send_with_sender(
                repository,
                user_id=message["user_id"],
                sender_id=message["sender_id"],
                to_email=message["to_email"],
                subject=message["subject"],
                body=message["body"],
            )
            repository.mark_sent(message["id"], provider_id)
        except Exception as exc:
            # Fail safe. We deliberately do not automatically retry an uncertain send,
            # because a timeout after Gmail accepted the message could create duplicates.
            repository.mark_failed(message["id"], str(exc))
            try:
                repository.sender_error(message["user_id"], message["sender_id"], str(exc))
            except Exception:
                pass
        processed += 1
    return processed


def main() -> None:
    print("Outreach worker started. Press Ctrl+C to stop.")
    while True:
        try:
            process_once()
        except KeyboardInterrupt:
            break
        except Exception as exc:
            print(f"Worker iteration failed: {exc}")
        time.sleep(5)


if __name__ == "__main__":
    main()
