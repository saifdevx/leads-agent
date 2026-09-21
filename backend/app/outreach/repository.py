from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db.client import TursoHttpClient
from app.outreach.rendering import render_template
from app.providers.security import CredentialCipher


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OutreachNotFoundError(LookupError):
    pass


class OutreachRepository:
    def __init__(self, database: TursoHttpClient, cipher: CredentialCipher):
        self.database = database
        self.cipher = cipher

    # Templates
    def list_templates(self, user_id):
        return self.database.execute(
            "SELECT id,name,category,subject,body,is_active,created_at,updated_at FROM email_templates WHERE user_id=? AND is_active=1 ORDER BY updated_at DESC",
            (user_id,),
        ).rows

    def get_template(self, user_id, template_id):
        rows = self.database.execute(
            "SELECT id,name,category,subject,body,is_active,created_at,updated_at FROM email_templates WHERE user_id=? AND id=?",
            (user_id, template_id),
        ).rows
        if not rows:
            raise OutreachNotFoundError("Template not found")
        return rows[0]

    def save_template(self, user_id, data, template_id=None):
        ts = now()
        tid = template_id or str(uuid4())
        if template_id:
            self.database.execute(
                "UPDATE email_templates SET name=?,category=?,subject=?,body=?,updated_at=? WHERE user_id=? AND id=?",
                (data.name, data.category, data.subject, data.body, ts, user_id, tid),
                want_rows=False,
            )
        else:
            self.database.execute(
                "INSERT INTO email_templates(id,user_id,name,category,subject,body,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?,1,?,?)",
                (tid, user_id, data.name, data.category, data.subject, data.body, ts, ts),
                want_rows=False,
            )
        return self.get_template(user_id, tid)

    def delete_template(self, user_id, template_id):
        self.database.execute(
            "UPDATE email_templates SET is_active=0,updated_at=? WHERE user_id=? AND id=?",
            (now(), user_id, template_id),
            want_rows=False,
        )

    # Senders
    def list_senders(self, user_id):
        return self.database.execute(
            "SELECT id,provider,email,display_name,status,last_error,created_at,updated_at FROM sender_connections WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,),
        ).rows

    def get_sender(self, user_id, sender_id, with_credentials=False):
        cols = "id,provider,email,display_name,status,last_error,created_at,updated_at" + (
            ",credentials_ciphertext" if with_credentials else ""
        )
        rows = self.database.execute(
            f"SELECT {cols} FROM sender_connections WHERE user_id=? AND id=?",
            (user_id, sender_id),
        ).rows
        if not rows:
            raise OutreachNotFoundError("Sender not found")
        row = rows[0]
        if with_credentials:
            row["credentials"] = self.cipher.decrypt(row.pop("credentials_ciphertext"))
        return row

    def save_gmail_sender(self, user_id, email, display_name, credentials):
        return self._save_sender(user_id, "gmail", email, display_name, credentials)

    def save_hostinger_sender(self, user_id, email, display_name, credentials):
        return self._save_sender(user_id, "hostinger", email, display_name, credentials)

    def _save_sender(self, user_id, provider, email, display_name, credentials):
        ts = now()
        encrypted = self.cipher.encrypt(credentials)
        existing = self.database.execute(
            "SELECT id FROM sender_connections WHERE user_id=? AND provider=? AND email=?",
            (user_id, provider, email),
        ).rows
        if existing:
            sid = existing[0]["id"]
            self.database.execute(
                "UPDATE sender_connections SET display_name=?,credentials_ciphertext=?,status='connected',last_error=NULL,updated_at=? WHERE id=? AND user_id=?",
                (display_name, encrypted, ts, sid, user_id),
                want_rows=False,
            )
        else:
            sid = str(uuid4())
            self.database.execute(
                "INSERT INTO sender_connections(id,user_id,provider,email,display_name,credentials_ciphertext,status,created_at,updated_at) VALUES(?,?,?,?,?,?,'connected',?,?)",
                (sid, user_id, provider, email, display_name, encrypted, ts, ts),
                want_rows=False,
            )
        return self.get_sender(user_id, sid)

    def update_sender_credentials(self, user_id, sender_id, credentials):
        self.database.execute(
            "UPDATE sender_connections SET credentials_ciphertext=?,status='connected',last_error=NULL,updated_at=? WHERE user_id=? AND id=?",
            (self.cipher.encrypt(credentials), now(), user_id, sender_id),
            want_rows=False,
        )

    def sender_error(self, user_id, sender_id, message):
        self.database.execute(
            "UPDATE sender_connections SET last_error=?,updated_at=? WHERE user_id=? AND id=?",
            (message[:500], now(), user_id, sender_id),
            want_rows=False,
        )

    def delete_sender(self, user_id, sender_id):
        self.database.execute(
            "DELETE FROM sender_connections WHERE user_id=? AND id=?",
            (user_id, sender_id),
            want_rows=False,
        )

    # Suppression
    def suppress(self, user_id, email, reason):
        value = email.strip().lower()
        ts = now()
        self.database.execute(
            "INSERT OR IGNORE INTO suppression_entries(id,user_id,email,reason,created_at) VALUES(?,?,?,?,?)",
            (str(uuid4()), user_id, value, reason, ts),
            want_rows=False,
        )

    def suppressed_emails(self, user_id, emails):
        if not emails:
            return set()
        values = [e.lower() for e in emails]
        placeholders = ",".join("?" for _ in values)
        rows = self.database.execute(
            f"SELECT email FROM suppression_entries WHERE user_id=? AND email IN ({placeholders})",
            (user_id, *values),
        ).rows
        return {str(r["email"]).lower() for r in rows}

    def is_suppressed(self, user_id, email):
        value = str(email or "").strip().lower()
        if not value:
            return False
        rows = self.database.execute(
            "SELECT 1 AS ok FROM suppression_entries WHERE user_id=? AND email=? LIMIT 1",
            (user_id, value),
        ).rows
        return bool(rows)

    # Campaigns
    def _campaign_row(self, user_id, campaign_id):
        rows = self.database.execute(
            """
            SELECT c.*, s.email AS sender_email FROM campaigns c
            LEFT JOIN sender_connections s ON s.id=c.sender_id
            WHERE c.user_id=? AND c.id=?
            """,
            (user_id, campaign_id),
        ).rows
        if not rows:
            raise OutreachNotFoundError("Campaign not found")
        return rows[0]

    def list_campaigns(self, user_id):
        return self.database.execute(
            """
            SELECT c.*, s.email AS sender_email FROM campaigns c
            LEFT JOIN sender_connections s ON s.id=c.sender_id
            WHERE c.user_id=? ORDER BY c.created_at DESC
            """,
            (user_id,),
        ).rows

    def create_campaign(self, user_id, data, lead_repository):
        template = self.get_template(user_id, data.template_id)
        sender = self.get_sender(user_id, data.sender_id)
        followup_templates = []
        for followup in data.follow_ups:
            followup_templates.append((followup, self.get_template(user_id, followup.template_id)))

        leads = lead_repository.get_leads_by_ids(user_id, data.lead_ids)
        emails = [str(l.get("email") or "").strip().lower() for l in leads if l.get("email")]
        suppressed = self.suppressed_emails(user_id, emails)
        valid = []
        missing = 0
        skipped = 0
        for lead in leads:
            email = str(lead.get("email") or "").strip().lower()
            if not email:
                missing += 1
                continue
            if email in suppressed:
                skipped += 1
                continue
            valid.append(lead)
        if not valid:
            raise ValueError("No selected leads have sendable email addresses.")

        ts = now()
        cid = str(uuid4())
        self.database.execute(
            """
            INSERT INTO campaigns(
                id,user_id,name,template_id,sender_id,status,daily_limit,send_start_hour,send_end_hour,
                timezone,min_interval_seconds,recipient_count,skipped_count,stop_on_reply,created_at,updated_at
            ) VALUES(?,?,?,?,?,'draft',?,?,?,?,?,?,?,?,?,?)
            """,
            (
                cid,
                user_id,
                data.name,
                data.template_id,
                data.sender_id,
                data.daily_limit,
                data.send_start_hour,
                data.send_end_hour,
                data.timezone,
                data.min_interval_seconds,
                len(valid),
                skipped,
                1 if data.stop_on_reply else 0,
                ts,
                ts,
            ),
            want_rows=False,
        )

        statements = [
            (
                "INSERT INTO campaign_steps(id,user_id,campaign_id,step_number,template_id,delay_hours,created_at) VALUES(?,?,?,?,?,?,?)",
                (str(uuid4()), user_id, cid, 0, data.template_id, 0, ts),
                False,
            )
        ]
        for index, (followup, _) in enumerate(followup_templates, start=1):
            statements.append(
                (
                    "INSERT INTO campaign_steps(id,user_id,campaign_id,step_number,template_id,delay_hours,created_at) VALUES(?,?,?,?,?,?,?)",
                    (str(uuid4()), user_id, cid, index, followup.template_id, followup.delay_hours, ts),
                    False,
                )
            )

        preview = []
        for lead in valid:
            all_templates = [(0, template)] + [(idx, tpl) for idx, (_, tpl) in enumerate(followup_templates, start=1)]
            for step_number, step_template in all_templates:
                subject = render_template(step_template["subject"], lead, sender)
                body = render_template(step_template["body"], lead, sender)
                status = "draft" if step_number == 0 else "waiting"
                kind = "initial" if step_number == 0 else "followup"
                mid = str(uuid4())
                statements.append(
                    (
                        """
                        INSERT INTO email_messages(
                            id,user_id,campaign_id,lead_id,sender_id,step_number,message_kind,to_email,subject,body,status,created_at,updated_at
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            mid,
                            user_id,
                            cid,
                            lead["id"],
                            data.sender_id,
                            step_number,
                            kind,
                            lead["email"],
                            subject,
                            body,
                            status,
                            ts,
                            ts,
                        ),
                        False,
                    )
                )
                if len(preview) < 5 and step_number == 0:
                    preview.append(
                        {
                            "lead_id": lead["id"],
                            "to_email": lead["email"],
                            "subject": subject,
                            "body": body,
                            "step_number": 0,
                        }
                    )
        self.database.execute_batch(statements)
        return self._campaign_row(user_id, cid), preview, skipped, missing

    def approve_campaign(self, user_id, campaign_id):
        campaign = self._campaign_row(user_id, campaign_id)
        if campaign["status"] not in ("draft", "paused"):
            raise ValueError("Only draft or paused campaigns can be approved.")
        ts = now()
        self.database.execute_batch(
            [
                (
                    "UPDATE campaigns SET status='sending',approved_at=COALESCE(approved_at,?),started_at=COALESCE(started_at,?),updated_at=? WHERE user_id=? AND id=?",
                    (ts, ts, ts, user_id, campaign_id),
                    False,
                ),
                (
                    "UPDATE email_messages SET status='queued',scheduled_at=COALESCE(scheduled_at,?),updated_at=? WHERE user_id=? AND campaign_id=? AND status='draft' AND step_number=0",
                    (ts, ts, user_id, campaign_id),
                    False,
                ),
            ]
        )
        return self._campaign_row(user_id, campaign_id)

    def set_campaign_status(self, user_id, campaign_id, status):
        allowed = {"paused", "sending", "cancelled"}
        if status not in allowed:
            raise ValueError("Invalid campaign state.")
        self._campaign_row(user_id, campaign_id)
        ts = now()
        self.database.execute(
            "UPDATE campaigns SET status=?,updated_at=? WHERE user_id=? AND id=?",
            (status, ts, user_id, campaign_id),
            want_rows=False,
        )
        if status == "cancelled":
            self.database.execute(
                "UPDATE email_messages SET status='cancelled',updated_at=? WHERE user_id=? AND campaign_id=? AND status IN ('draft','waiting','queued')",
                (ts, user_id, campaign_id),
                want_rows=False,
            )
        return self._campaign_row(user_id, campaign_id)

    def delete_campaign(self, user_id, campaign_id):
        campaign = self._campaign_row(user_id, campaign_id)
        if campaign["status"] == "sending":
            raise ValueError("Pause or cancel a sending campaign before deleting it.")
        self.database.execute_batch(
            [
                ("DELETE FROM inbound_replies WHERE user_id=? AND campaign_id=?", (user_id, campaign_id), False),
                ("DELETE FROM campaign_steps WHERE user_id=? AND campaign_id=?", (user_id, campaign_id), False),
                ("DELETE FROM email_messages WHERE user_id=? AND campaign_id=?", (user_id, campaign_id), False),
                ("DELETE FROM campaigns WHERE user_id=? AND id=?", (user_id, campaign_id), False),
            ]
        )
        return True

    def campaign_preview(self, user_id, campaign_id, limit=5):
        self._campaign_row(user_id, campaign_id)
        return self.database.execute(
            "SELECT lead_id,to_email,subject,body,step_number FROM email_messages WHERE user_id=? AND campaign_id=? AND step_number=0 ORDER BY created_at LIMIT ?",
            (user_id, campaign_id, limit),
        ).rows

    def campaign_detail(self, user_id, campaign_id):
        campaign = self._campaign_row(user_id, campaign_id)
        steps = self.database.execute(
            """
            SELECT cs.id,cs.step_number,cs.template_id,cs.delay_hours,t.name AS template_name
            FROM campaign_steps cs LEFT JOIN email_templates t ON t.id=cs.template_id
            WHERE cs.user_id=? AND cs.campaign_id=? ORDER BY cs.step_number
            """,
            (user_id, campaign_id),
        ).rows
        messages = self.database.execute(
            """
            SELECT m.id,m.lead_id,l.company_name,
                   TRIM(COALESCE(l.first_name,'') || ' ' || COALESCE(l.last_name,'')) AS contact_name,
                   m.to_email,m.step_number,m.message_kind,m.subject,m.status,m.scheduled_at,m.sent_at,m.replied_at,m.last_error
            FROM email_messages m LEFT JOIN leads l ON l.id=m.lead_id
            WHERE m.user_id=? AND m.campaign_id=? ORDER BY m.lead_id,m.step_number
            """,
            (user_id, campaign_id),
        ).rows
        replies = self.list_replies(user_id, campaign_id=campaign_id)
        followups_sent = sum(1 for m in messages if int(m.get("step_number") or 0) > 0 and m.get("status") == "sent")
        recipients = max(int(campaign.get("recipient_count") or 0), 1)
        reply_rate = round((int(campaign.get("replied_count") or 0) / recipients) * 100, 1)
        return campaign, steps, messages, replies, followups_sent, reply_rate

    def retry_failed_message(self, user_id, campaign_id, message_id):
        campaign = self._campaign_row(user_id, campaign_id)
        if campaign["status"] in {"cancelled", "completed"}:
            raise ValueError("This campaign is no longer accepting retries.")
        rows = self.database.execute(
            "SELECT id,to_email,lead_id FROM email_messages WHERE user_id=? AND campaign_id=? AND id=? AND status='failed'",
            (user_id, campaign_id, message_id),
        ).rows
        if not rows:
            raise ValueError("Only failed messages can be retried.")
        message = rows[0]
        if self.is_suppressed(user_id, message["to_email"]):
            raise ValueError("This recipient is suppressed.")
        if self._lead_has_reply(campaign_id, message["lead_id"]):
            raise ValueError("This recipient already replied.")
        ts = now()
        self.database.execute_batch(
            [
                (
                    "UPDATE email_messages SET status='queued',scheduled_at=?,last_error=NULL,updated_at=? WHERE id=? AND user_id=?",
                    (ts, ts, message_id, user_id),
                    False,
                ),
                (
                    "UPDATE campaigns SET failed_count=CASE WHEN failed_count>0 THEN failed_count-1 ELSE 0 END,status=CASE WHEN status='paused' THEN status ELSE 'sending' END,updated_at=? WHERE id=? AND user_id=?",
                    (ts, campaign_id, user_id),
                    False,
                ),
            ]
        )

    # Worker
    def due_messages(self, limit=10):
        return self.database.execute(
            """
            SELECT m.*, c.daily_limit,c.send_start_hour,c.send_end_hour,c.timezone,c.min_interval_seconds,
                   c.status AS campaign_status,c.stop_on_reply,s.email AS sender_email,s.display_name
            FROM email_messages m JOIN campaigns c ON c.id=m.campaign_id JOIN sender_connections s ON s.id=m.sender_id
            WHERE m.status='queued' AND c.status='sending' AND (m.scheduled_at IS NULL OR m.scheduled_at<=?)
            ORDER BY COALESCE(m.scheduled_at,m.created_at),m.created_at LIMIT ?
            """,
            (now(), limit),
        ).rows

    def claim_message(self, message_id):
        result = self.database.execute(
            "UPDATE email_messages SET status='sending',updated_at=? WHERE id=? AND status='queued'",
            (now(), message_id),
            want_rows=False,
        )
        return result.affected_row_count == 1

    def sent_today_count(self, sender_id, start_utc, end_utc):
        rows = self.database.execute(
            "SELECT COUNT(*) AS n FROM email_messages WHERE sender_id=? AND status='sent' AND sent_at>=? AND sent_at<?",
            (sender_id, start_utc, end_utc),
        ).rows
        return int(rows[0]["n"] if rows else 0)

    def last_sent_at(self, sender_id):
        rows = self.database.execute(
            "SELECT sent_at FROM email_messages WHERE sender_id=? AND status='sent' ORDER BY sent_at DESC LIMIT 1",
            (sender_id,),
        ).rows
        return rows[0]["sent_at"] if rows else None

    def mark_sent(self, message_id, provider_message_id):
        ts = now()
        rows = self.database.execute(
            "SELECT campaign_id,lead_id,step_number FROM email_messages WHERE id=?",
            (message_id,),
        ).rows
        if not rows:
            return
        row = rows[0]
        cid = row["campaign_id"]
        lead_id = row["lead_id"]
        step_number = int(row.get("step_number") or 0)
        statements = [
            (
                "UPDATE email_messages SET status='sent',provider_message_id=?,sent_at=?,updated_at=? WHERE id=?",
                (provider_message_id, ts, ts, message_id),
                False,
            ),
            ("UPDATE campaigns SET sent_count=sent_count+1,updated_at=? WHERE id=?", (ts, cid), False),
        ]
        next_rows = self.database.execute(
            """
            SELECT m.id,cs.delay_hours FROM email_messages m
            JOIN campaign_steps cs ON cs.campaign_id=m.campaign_id AND cs.step_number=m.step_number
            WHERE m.campaign_id=? AND m.lead_id=? AND m.step_number=? AND m.status='waiting' LIMIT 1
            """,
            (cid, lead_id, step_number + 1),
        ).rows
        if next_rows and not self._lead_has_reply(cid, lead_id):
            delay = int(next_rows[0].get("delay_hours") or 72)
            scheduled = (datetime.now(timezone.utc) + timedelta(hours=delay)).isoformat()
            statements.append(
                (
                    "UPDATE email_messages SET status='queued',scheduled_at=?,updated_at=? WHERE id=? AND status='waiting'",
                    (scheduled, ts, next_rows[0]["id"]),
                    False,
                )
            )
        self.database.execute_batch(statements)
        self._finish_if_done(cid)

    def mark_failed(self, message_id, error):
        ts = now()
        rows = self.database.execute(
            "SELECT campaign_id,lead_id FROM email_messages WHERE id=?",
            (message_id,),
        ).rows
        if not rows:
            return
        cid = rows[0]["campaign_id"]
        lead_id = rows[0]["lead_id"]
        self.database.execute_batch(
            [
                (
                    "UPDATE email_messages SET status='failed',last_error=?,updated_at=? WHERE id=?",
                    (error[:500], ts, message_id),
                    False,
                ),
                (
                    "UPDATE email_messages SET status='cancelled',updated_at=? WHERE campaign_id=? AND lead_id=? AND status='waiting'",
                    (ts, cid, lead_id),
                    False,
                ),
                ("UPDATE campaigns SET failed_count=failed_count+1,updated_at=? WHERE id=?", (ts, cid), False),
            ]
        )
        self._finish_if_done(cid)

    def requeue(self, message_id, scheduled_at):
        self.database.execute(
            "UPDATE email_messages SET status='queued',scheduled_at=?,updated_at=? WHERE id=?",
            (scheduled_at, now(), message_id),
            want_rows=False,
        )

    def _finish_if_done(self, campaign_id):
        rows = self.database.execute(
            "SELECT COUNT(*) AS n FROM email_messages WHERE campaign_id=? AND status IN ('draft','waiting','queued','sending')",
            (campaign_id,),
        ).rows
        if rows and int(rows[0]["n"]) == 0:
            ts = now()
            self.database.execute(
                "UPDATE campaigns SET status='completed',completed_at=?,updated_at=? WHERE id=? AND status='sending'",
                (ts, ts, campaign_id),
                want_rows=False,
            )

    # Replies / inbox
    def list_replies(self, user_id, campaign_id=None, limit=200):
        where = "r.user_id=?"
        params = [user_id]
        if campaign_id:
            where += " AND r.campaign_id=?"
            params.append(campaign_id)
        params.append(limit)
        return self.database.execute(
            f"""
            SELECT r.id,r.campaign_id,c.name AS campaign_name,r.lead_id,l.company_name,
                   r.from_email,r.to_email,r.subject,r.snippet,r.body_text,r.classification,r.received_at
            FROM inbound_replies r
            LEFT JOIN campaigns c ON c.id=r.campaign_id
            LEFT JOIN leads l ON l.id=r.lead_id
            WHERE {where}
            ORDER BY r.received_at DESC LIMIT ?
            """,
            tuple(params),
        ).rows

    def _lead_has_reply(self, campaign_id, lead_id):
        rows = self.database.execute(
            "SELECT 1 AS ok FROM inbound_replies WHERE campaign_id=? AND lead_id=? LIMIT 1",
            (campaign_id, lead_id),
        ).rows
        return bool(rows)

    def has_sent_to(self, user_id: str, sender_id: str, email: str) -> bool:
        value = str(email or "").strip().lower()
        if not value:
            return False
        rows = self.database.execute(
            "SELECT 1 AS ok FROM email_messages WHERE user_id=? AND sender_id=? AND lower(to_email)=? AND status='sent' LIMIT 1",
            (user_id, sender_id, value),
        ).rows
        return bool(rows)

    def classify_reply(self, subject: str | None, body: str | None) -> str:
        text = f"{subject or ''}\n{body or ''}".lower()
        unsubscribe = ("unsubscribe", "remove me", "stop emailing", "do not contact", "don't contact", "opt out")
        out_of_office = ("out of office", "automatic reply", "auto-reply", "away from the office", "on vacation")
        interested = ("interested", "sounds good", "let's talk", "lets talk", "book a call", "schedule", "send me", "tell me more", "yes,")
        negative = ("not interested", "no thanks", "not a fit", "don't need", "do not need")
        if any(term in text for term in unsubscribe):
            return "unsubscribe"
        if any(term in text for term in out_of_office):
            return "out_of_office"
        if any(term in text for term in negative):
            return "not_interested"
        if any(term in text for term in interested):
            return "interested"
        return "reply"

    def record_reply(
        self,
        *,
        user_id: str,
        sender_id: str,
        from_email: str,
        to_email: str | None,
        subject: str | None,
        snippet: str | None,
        body_text: str | None,
        provider_uid: str,
        provider_message_id: str | None,
        received_at: str | None,
    ) -> bool:
        from_email = str(from_email or "").strip().lower()
        if not from_email or not provider_uid:
            return False
        exists = self.database.execute(
            "SELECT 1 AS ok FROM inbound_replies WHERE sender_id=? AND provider_uid=? LIMIT 1",
            (sender_id, provider_uid),
        ).rows
        if exists:
            return False

        match = self.database.execute(
            """
            SELECT m.campaign_id,m.lead_id,c.stop_on_reply
            FROM email_messages m JOIN campaigns c ON c.id=m.campaign_id
            WHERE m.user_id=? AND m.sender_id=? AND lower(m.to_email)=? AND m.status='sent'
            ORDER BY m.sent_at DESC LIMIT 1
            """,
            (user_id, sender_id, from_email),
        ).rows
        if not match:
            return False
        campaign_id = match[0]["campaign_id"]
        lead_id = match[0]["lead_id"]
        stop_on_reply = bool(int(match[0].get("stop_on_reply") or 0))
        classification = self.classify_reply(subject, body_text or snippet)
        had_prior_reply = self._lead_has_reply(campaign_id, lead_id)
        ts = received_at or now()
        rid = str(uuid4())
        statements = [
            (
                """
                INSERT INTO inbound_replies(
                    id,user_id,sender_id,campaign_id,lead_id,from_email,to_email,subject,snippet,body_text,
                    provider_uid,provider_message_id,classification,received_at,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    rid,
                    user_id,
                    sender_id,
                    campaign_id,
                    lead_id,
                    from_email,
                    to_email,
                    subject,
                    snippet,
                    body_text,
                    provider_uid,
                    provider_message_id,
                    classification,
                    ts,
                    now(),
                ),
                False,
            )
        ]
        if campaign_id and lead_id:
            replied_delta = 0 if had_prior_reply else 1
            interested_delta = 1 if (not had_prior_reply and classification == "interested") else 0
            unsub_delta = 1 if (not had_prior_reply and classification == "unsubscribe") else 0
            ooo_delta = 1 if (not had_prior_reply and classification == "out_of_office") else 0
            statements.extend(
                [
                    (
                        "UPDATE campaigns SET replied_count=replied_count+?,interested_count=interested_count+?,unsubscribed_count=unsubscribed_count+?,out_of_office_count=out_of_office_count+?,updated_at=? WHERE id=?",
                        (replied_delta, interested_delta, unsub_delta, ooo_delta, now(), campaign_id),
                        False,
                    ),
                    (
                        "UPDATE email_messages SET replied_at=COALESCE(replied_at,?),updated_at=? WHERE campaign_id=? AND lead_id=? AND status='sent'",
                        (ts, now(), campaign_id, lead_id),
                        False,
                    ),
                ]
            )
            if stop_on_reply:
                statements.append(
                    (
                        "UPDATE email_messages SET status='cancelled',updated_at=? WHERE campaign_id=? AND lead_id=? AND status IN ('draft','waiting','queued')",
                        (now(), campaign_id, lead_id),
                        False,
                    )
                )
        self.database.execute_batch(statements)
        if classification == "unsubscribe":
            self.suppress(user_id, from_email, "reply_unsubscribe")
        if campaign_id:
            self._finish_if_done(campaign_id)
        return True
