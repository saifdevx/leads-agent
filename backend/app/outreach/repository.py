from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import uuid4
from app.db.client import TursoHttpClient
from app.providers.security import CredentialCipher
from app.outreach.rendering import render_template

def now() -> str: return datetime.now(timezone.utc).isoformat()

class OutreachNotFoundError(LookupError): pass

class OutreachRepository:
    def __init__(self, database: TursoHttpClient, cipher: CredentialCipher):
        self.database=database; self.cipher=cipher

    # Templates
    def list_templates(self, user_id):
        return self.database.execute("SELECT id,name,category,subject,body,is_active,created_at,updated_at FROM email_templates WHERE user_id=? AND is_active=1 ORDER BY updated_at DESC", (user_id,)).rows
    def get_template(self,user_id,template_id):
        rows=self.database.execute("SELECT id,name,category,subject,body,is_active,created_at,updated_at FROM email_templates WHERE user_id=? AND id=?",(user_id,template_id)).rows
        if not rows: raise OutreachNotFoundError("Template not found")
        return rows[0]
    def save_template(self,user_id,data,template_id=None):
        ts=now(); tid=template_id or str(uuid4())
        if template_id:
            self.database.execute("UPDATE email_templates SET name=?,category=?,subject=?,body=?,updated_at=? WHERE user_id=? AND id=?",(data.name,data.category,data.subject,data.body,ts,user_id,tid),want_rows=False)
        else:
            self.database.execute("INSERT INTO email_templates(id,user_id,name,category,subject,body,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?,1,?,?)",(tid,user_id,data.name,data.category,data.subject,data.body,ts,ts),want_rows=False)
        return self.get_template(user_id,tid)
    def delete_template(self,user_id,template_id):
        self.database.execute("UPDATE email_templates SET is_active=0,updated_at=? WHERE user_id=? AND id=?",(now(),user_id,template_id),want_rows=False)

    # Senders
    def list_senders(self,user_id):
        return self.database.execute("SELECT id,provider,email,display_name,status,last_error,created_at,updated_at FROM sender_connections WHERE user_id=? ORDER BY updated_at DESC",(user_id,)).rows
    def get_sender(self,user_id,sender_id,with_credentials=False):
        cols="id,provider,email,display_name,status,last_error,created_at,updated_at" + (",credentials_ciphertext" if with_credentials else "")
        rows=self.database.execute(f"SELECT {cols} FROM sender_connections WHERE user_id=? AND id=?",(user_id,sender_id)).rows
        if not rows: raise OutreachNotFoundError("Sender not found")
        row=rows[0]
        if with_credentials: row["credentials"]=self.cipher.decrypt(row.pop("credentials_ciphertext"))
        return row
    def save_gmail_sender(self,user_id,email,display_name,credentials):
        ts=now(); encrypted=self.cipher.encrypt(credentials)
        existing=self.database.execute("SELECT id FROM sender_connections WHERE user_id=? AND provider='gmail' AND email=?",(user_id,email)).rows
        if existing:
            sid=existing[0]["id"]
            self.database.execute("UPDATE sender_connections SET display_name=?,credentials_ciphertext=?,status='connected',last_error=NULL,updated_at=? WHERE id=? AND user_id=?",(display_name,encrypted,ts,sid,user_id),want_rows=False)
        else:
            sid=str(uuid4())
            self.database.execute("INSERT INTO sender_connections(id,user_id,provider,email,display_name,credentials_ciphertext,status,created_at,updated_at) VALUES(?, ?, 'gmail', ?, ?, ?, 'connected', ?, ?)", (sid, user_id, email, display_name, encrypted, ts, ts), want_rows=False)
        return self.get_sender(user_id,sid)
    def save_hostinger_sender(self,user_id,email,display_name,credentials):
        ts=now(); encrypted=self.cipher.encrypt(credentials)
        existing=self.database.execute("SELECT id FROM sender_connections WHERE user_id=? AND provider='hostinger' AND email=?",(user_id,email)).rows
        if existing:
            sid=existing[0]["id"]
            self.database.execute("UPDATE sender_connections SET display_name=?,credentials_ciphertext=?,status='connected',last_error=NULL,updated_at=? WHERE id=? AND user_id=?",(display_name,encrypted,ts,sid,user_id),want_rows=False)
        else:
            sid=str(uuid4())
            self.database.execute("INSERT INTO sender_connections(id,user_id,provider,email,display_name,credentials_ciphertext,status,created_at,updated_at) VALUES(?, ?, 'hostinger', ?, ?, ?, 'connected', ?, ?)", (sid, user_id, email, display_name, encrypted, ts, ts), want_rows=False)
        return self.get_sender(user_id,sid)
    def update_sender_credentials(self,user_id,sender_id,credentials):
        self.database.execute("UPDATE sender_connections SET credentials_ciphertext=?,status='connected',last_error=NULL,updated_at=? WHERE user_id=? AND id=?",(self.cipher.encrypt(credentials),now(),user_id,sender_id),want_rows=False)
    def sender_error(self,user_id,sender_id,message):
        self.database.execute("UPDATE sender_connections SET last_error=?,updated_at=? WHERE user_id=? AND id=?",(message[:500],now(),user_id,sender_id),want_rows=False)
    def delete_sender(self,user_id,sender_id):
        self.database.execute("DELETE FROM sender_connections WHERE user_id=? AND id=?",(user_id,sender_id),want_rows=False)

    # Suppression
    def suppress(self,user_id,email,reason):
        value=email.strip().lower(); ts=now()
        self.database.execute("INSERT OR IGNORE INTO suppression_entries(id,user_id,email,reason,created_at) VALUES(?,?,?,?,?)",(str(uuid4()),user_id,value,reason,ts),want_rows=False)
    def suppressed_emails(self,user_id,emails):
        if not emails: return set()
        values=[e.lower() for e in emails]
        placeholders=','.join('?' for _ in values)
        rows=self.database.execute(f"SELECT email FROM suppression_entries WHERE user_id=? AND email IN ({placeholders})",(user_id,*values)).rows
        return {str(r['email']).lower() for r in rows}

    # Campaigns
    def _campaign_row(self,user_id,campaign_id):
        rows=self.database.execute("""
          SELECT c.*, s.email AS sender_email FROM campaigns c
          LEFT JOIN sender_connections s ON s.id=c.sender_id
          WHERE c.user_id=? AND c.id=?
        """,(user_id,campaign_id)).rows
        if not rows: raise OutreachNotFoundError("Campaign not found")
        return rows[0]
    def list_campaigns(self,user_id):
        return self.database.execute("""
          SELECT c.*, s.email AS sender_email FROM campaigns c
          LEFT JOIN sender_connections s ON s.id=c.sender_id
          WHERE c.user_id=? ORDER BY c.created_at DESC
        """,(user_id,)).rows
    def create_campaign(self,user_id,data,lead_repository):
        template=self.get_template(user_id,data.template_id); sender=self.get_sender(user_id,data.sender_id)
        leads=lead_repository.get_leads_by_ids(user_id,data.lead_ids)
        emails=[str(l.get('email') or '').strip().lower() for l in leads if l.get('email')]
        suppressed=self.suppressed_emails(user_id,emails)
        valid=[]; missing=0; skipped=0
        for lead in leads:
            email=str(lead.get('email') or '').strip().lower()
            if not email: missing+=1; continue
            if email in suppressed: skipped+=1; continue
            valid.append(lead)
        if not valid: raise ValueError("No selected leads have sendable email addresses.")
        ts=now(); cid=str(uuid4())
        self.database.execute("""
          INSERT INTO campaigns(id,user_id,name,template_id,sender_id,status,daily_limit,send_start_hour,send_end_hour,timezone,min_interval_seconds,recipient_count,skipped_count,created_at,updated_at)
          VALUES(?,?,?,?,?,'draft',?,?,?,?,?,?,?, ?,?)
        """,(cid,user_id,data.name,data.template_id,data.sender_id,data.daily_limit,data.send_start_hour,data.send_end_hour,data.timezone,data.min_interval_seconds,len(valid),skipped,ts,ts),want_rows=False)
        statements=[]; preview=[]
        for lead in valid:
            subject=render_template(template['subject'],lead,sender); body=render_template(template['body'],lead,sender)
            mid=str(uuid4())
            statements.append(("INSERT INTO email_messages(id,user_id,campaign_id,lead_id,sender_id,to_email,subject,body,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,'draft',?,?)",(mid,user_id,cid,lead['id'],data.sender_id,lead['email'],subject,body,ts,ts),False))
            if len(preview)<3: preview.append({'lead_id':lead['id'],'to_email':lead['email'],'subject':subject,'body':body})
        self.database.execute_batch(statements)
        return self._campaign_row(user_id,cid),preview,skipped,missing
    def approve_campaign(self,user_id,campaign_id):
        campaign=self._campaign_row(user_id,campaign_id)
        if campaign['status'] not in ('draft','paused'): raise ValueError("Only draft or paused campaigns can be approved.")
        ts=now()
        self.database.execute_batch([
          ("UPDATE campaigns SET status='sending',approved_at=COALESCE(approved_at,?),started_at=COALESCE(started_at,?),updated_at=? WHERE user_id=? AND id=?",(ts,ts,ts,user_id,campaign_id),False),
          ("UPDATE email_messages SET status='queued',scheduled_at=COALESCE(scheduled_at,?),updated_at=? WHERE user_id=? AND campaign_id=? AND status='draft'",(ts,ts,user_id,campaign_id),False),
        ])
        return self._campaign_row(user_id,campaign_id)
    def set_campaign_status(self,user_id,campaign_id,status):
        allowed={'paused','sending','cancelled'}
        if status not in allowed: raise ValueError('Invalid campaign state.')
        self.database.execute("UPDATE campaigns SET status=?,updated_at=? WHERE user_id=? AND id=?",(status,now(),user_id,campaign_id),want_rows=False)
        if status=='cancelled': self.database.execute("UPDATE email_messages SET status='cancelled',updated_at=? WHERE user_id=? AND campaign_id=? AND status IN ('draft','queued')",(now(),user_id,campaign_id),want_rows=False)
        return self._campaign_row(user_id,campaign_id)
    def campaign_preview(self,user_id,campaign_id,limit=5):
        self._campaign_row(user_id,campaign_id)
        return self.database.execute("SELECT lead_id,to_email,subject,body FROM email_messages WHERE user_id=? AND campaign_id=? ORDER BY created_at LIMIT ?",(user_id,campaign_id,limit)).rows

    # Worker
    def due_messages(self,limit=10):
        return self.database.execute("""
          SELECT m.*, c.daily_limit,c.send_start_hour,c.send_end_hour,c.timezone,c.min_interval_seconds,c.status AS campaign_status,s.email AS sender_email,s.display_name
          FROM email_messages m JOIN campaigns c ON c.id=m.campaign_id JOIN sender_connections s ON s.id=m.sender_id
          WHERE m.status='queued' AND c.status='sending' AND (m.scheduled_at IS NULL OR m.scheduled_at<=?)
          ORDER BY m.created_at LIMIT ?
        """,(now(),limit)).rows
    def claim_message(self,message_id):
        result=self.database.execute("UPDATE email_messages SET status='sending',updated_at=? WHERE id=? AND status='queued'",(now(),message_id),want_rows=False)
        return result.affected_row_count==1
    def sent_today_count(self,sender_id,start_utc,end_utc):
        rows=self.database.execute("SELECT COUNT(*) AS n FROM email_messages WHERE sender_id=? AND status='sent' AND sent_at>=? AND sent_at<?",(sender_id,start_utc,end_utc)).rows
        return int(rows[0]['n'] if rows else 0)
    def last_sent_at(self,sender_id):
        rows=self.database.execute("SELECT sent_at FROM email_messages WHERE sender_id=? AND status='sent' ORDER BY sent_at DESC LIMIT 1",(sender_id,)).rows
        return rows[0]['sent_at'] if rows else None
    def mark_sent(self,message_id,provider_message_id):
        ts=now(); rows=self.database.execute("SELECT campaign_id FROM email_messages WHERE id=?",(message_id,)).rows
        if not rows: return
        cid=rows[0]['campaign_id']
        self.database.execute_batch([
          ("UPDATE email_messages SET status='sent',provider_message_id=?,sent_at=?,updated_at=? WHERE id=?",(provider_message_id,ts,ts,message_id),False),
          ("UPDATE campaigns SET sent_count=sent_count+1,updated_at=? WHERE id=?",(ts,cid),False),
        ])
        self._finish_if_done(cid)
    def mark_failed(self,message_id,error):
        ts=now(); rows=self.database.execute("SELECT campaign_id FROM email_messages WHERE id=?",(message_id,)).rows
        if not rows:return
        cid=rows[0]['campaign_id']
        self.database.execute_batch([
          ("UPDATE email_messages SET status='failed',last_error=?,updated_at=? WHERE id=?",(error[:500],ts,message_id),False),
          ("UPDATE campaigns SET failed_count=failed_count+1,updated_at=? WHERE id=?",(ts,cid),False),
        ])
        self._finish_if_done(cid)
    def requeue(self,message_id,scheduled_at):
        self.database.execute("UPDATE email_messages SET status='queued',scheduled_at=?,updated_at=? WHERE id=?",(scheduled_at,now(),message_id),want_rows=False)
    def _finish_if_done(self,campaign_id):
        rows=self.database.execute("SELECT COUNT(*) AS n FROM email_messages WHERE campaign_id=? AND status IN ('draft','queued','sending')",(campaign_id,)).rows
        if rows and int(rows[0]['n'])==0:
            ts=now(); self.database.execute("UPDATE campaigns SET status='completed',completed_at=?,updated_at=? WHERE id=? AND status='sending'",(ts,ts,campaign_id),want_rows=False)
