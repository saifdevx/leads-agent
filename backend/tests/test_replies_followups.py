import pathlib
import sqlite3
from datetime import datetime, timezone

from cryptography.fernet import Fernet

from app.outreach.repository import OutreachRepository
from app.outreach.schemas import CampaignCreate, FollowUpCreate, TemplateCreate
from app.providers.security import CredentialCipher


class Result:
    def __init__(self, affected, rows):
        self.affected_row_count = affected
        self.rows = rows


class SqliteAdapter:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        root = pathlib.Path(__file__).resolve().parents[1]
        for file in sorted((root / "migrations").glob("*.sql")):
            self.conn.executescript(file.read_text())

    def execute(self, sql, params=(), want_rows=True):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        rows = [dict(r) for r in cur.fetchall()] if want_rows else []
        return Result(cur.rowcount if cur.rowcount != -1 else 0, rows)

    def execute_batch(self, statements):
        return [self.execute(sql, params, want) for sql, params, want in statements]


class Leads:
    def get_leads_by_ids(self, user_id, ids):
        return [{
            "id": "lead-1",
            "company_name": "Acme Solar",
            "first_name": "Sam",
            "last_name": "Lee",
            "job_title": "Owner",
            "email": "sam@acme.test",
            "website": "https://acme.test",
            "domain": "acme.test",
            "city": "Dallas",
            "region": "Texas",
            "country": "USA",
        }]


def repo():
    return OutreachRepository(SqliteAdapter(), CredentialCipher(Fernet.generate_key().decode()))


def setup_campaign(repository: OutreachRepository):
    initial = repository.save_template("u", TemplateCreate(name="Initial", category="General", subject="Hi", body="Hello"))
    follow = repository.save_template("u", TemplateCreate(name="Follow", category="General", subject="Following up", body="Checking in"))
    sender = repository.save_hostinger_sender("u", "sender@example.com", "Sender", {"api_token": "x", "mailbox_resource_id": "AC123"})
    campaign, _, _, _ = repository.create_campaign(
        "u",
        CampaignCreate(
            name="Sequence",
            lead_ids=["lead-1"],
            template_id=initial["id"],
            sender_id=sender["id"],
            follow_ups=[FollowUpCreate(template_id=follow["id"], delay_hours=24)],
        ),
        Leads(),
    )
    return campaign, sender


def test_followup_waits_until_initial_message_is_sent():
    repository = repo()
    campaign, _ = setup_campaign(repository)
    repository.approve_campaign("u", campaign["id"])
    due = repository.due_messages()
    assert len(due) == 1
    assert due[0]["step_number"] == 0
    repository.mark_sent(due[0]["id"], "provider-1")
    rows = repository.database.execute(
        "SELECT step_number,status,scheduled_at FROM email_messages WHERE campaign_id=? ORDER BY step_number",
        (campaign["id"],),
    ).rows
    assert rows[0]["status"] == "sent"
    assert rows[1]["status"] == "queued"
    assert rows[1]["scheduled_at"] is not None


def test_reply_stops_future_followups_and_counts_interested():
    repository = repo()
    campaign, sender = setup_campaign(repository)
    repository.approve_campaign("u", campaign["id"])
    first = repository.due_messages()[0]
    repository.mark_sent(first["id"], "provider-1")
    created = repository.record_reply(
        user_id="u",
        sender_id=sender["id"],
        from_email="sam@acme.test",
        to_email="sender@example.com",
        subject="Re: Hi",
        snippet="Yes, I am interested. Tell me more.",
        body_text="Yes, I am interested. Tell me more.",
        provider_uid="42",
        provider_message_id="<reply@example.com>",
        received_at=datetime.now(timezone.utc).isoformat(),
    )
    assert created is True
    follow = repository.database.execute(
        "SELECT status FROM email_messages WHERE campaign_id=? AND step_number=1",
        (campaign["id"],),
    ).rows[0]
    assert follow["status"] == "cancelled"
    refreshed = repository._campaign_row("u", campaign["id"])
    assert refreshed["replied_count"] == 1
    assert refreshed["interested_count"] == 1


def test_unsubscribe_reply_adds_suppression():
    repository = repo()
    campaign, sender = setup_campaign(repository)
    repository.approve_campaign("u", campaign["id"])
    first = repository.due_messages()[0]
    repository.mark_sent(first["id"], "provider-1")
    repository.record_reply(
        user_id="u",
        sender_id=sender["id"],
        from_email="sam@acme.test",
        to_email="sender@example.com",
        subject="Re: Hi",
        snippet="Please unsubscribe me",
        body_text="Please unsubscribe me",
        provider_uid="43",
        provider_message_id=None,
        received_at=None,
    )
    assert repository.is_suppressed("u", "sam@acme.test") is True


def test_duplicate_provider_uid_does_not_double_count_reply():
    repository = repo()
    campaign, sender = setup_campaign(repository)
    repository.approve_campaign("u", campaign["id"])
    first = repository.due_messages()[0]
    repository.mark_sent(first["id"], "provider-1")
    args = dict(
        user_id="u", sender_id=sender["id"], from_email="sam@acme.test", to_email="sender@example.com",
        subject="Re: Hi", snippet="Thanks", body_text="Thanks", provider_uid="44", provider_message_id=None, received_at=None,
    )
    assert repository.record_reply(**args) is True
    assert repository.record_reply(**args) is False
    refreshed = repository._campaign_row("u", campaign["id"])
    assert refreshed["replied_count"] == 1


def test_multiple_replies_from_same_lead_count_once_for_campaign_reply_rate():
    repository = repo()
    campaign, sender = setup_campaign(repository)
    repository.approve_campaign("u", campaign["id"])
    first = repository.due_messages()[0]
    repository.mark_sent(first["id"], "provider-1")

    for uid, text in (("51", "Thanks, tell me more"), ("52", "Sounds good")):
        assert repository.record_reply(
            user_id="u",
            sender_id=sender["id"],
            from_email="sam@acme.test",
            to_email="sender@example.com",
            subject="Re: Hi",
            snippet=text,
            body_text=text,
            provider_uid=uid,
            provider_message_id=None,
            received_at=None,
        ) is True

    refreshed = repository._campaign_row("u", campaign["id"])
    assert refreshed["replied_count"] == 1
