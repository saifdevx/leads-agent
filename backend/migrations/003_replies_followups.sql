ALTER TABLE campaigns ADD COLUMN stop_on_reply INTEGER NOT NULL DEFAULT 1;
ALTER TABLE campaigns ADD COLUMN replied_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE campaigns ADD COLUMN interested_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE campaigns ADD COLUMN unsubscribed_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE campaigns ADD COLUMN out_of_office_count INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS campaign_steps (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    template_id TEXT NOT NULL,
    delay_hours INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(campaign_id, step_number)
);
CREATE INDEX IF NOT EXISTS idx_campaign_steps_campaign ON campaign_steps(campaign_id, step_number);

DROP INDEX IF EXISTS idx_email_messages_queue;
DROP INDEX IF EXISTS idx_email_messages_campaign;
DROP INDEX IF EXISTS idx_email_messages_sender_sent;
ALTER TABLE email_messages RENAME TO email_messages_legacy;

CREATE TABLE email_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    step_number INTEGER NOT NULL DEFAULT 0,
    message_kind TEXT NOT NULL DEFAULT 'initial',
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    scheduled_at TEXT,
    sent_at TEXT,
    replied_at TEXT,
    provider_message_id TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(campaign_id, lead_id, step_number)
);

INSERT INTO email_messages (
    id,user_id,campaign_id,lead_id,sender_id,step_number,message_kind,to_email,subject,body,status,
    scheduled_at,sent_at,replied_at,provider_message_id,last_error,created_at,updated_at
)
SELECT
    id,user_id,campaign_id,lead_id,sender_id,0,'initial',to_email,subject,body,status,
    scheduled_at,sent_at,NULL,provider_message_id,last_error,created_at,updated_at
FROM email_messages_legacy;

DROP TABLE email_messages_legacy;
CREATE INDEX idx_email_messages_queue ON email_messages(status, scheduled_at, created_at);
CREATE INDEX idx_email_messages_campaign ON email_messages(campaign_id, status, step_number);
CREATE INDEX idx_email_messages_sender_sent ON email_messages(sender_id, sent_at);
CREATE INDEX idx_email_messages_lead ON email_messages(campaign_id, lead_id, step_number);

CREATE TABLE IF NOT EXISTS inbound_replies (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    campaign_id TEXT,
    lead_id TEXT,
    from_email TEXT NOT NULL,
    to_email TEXT,
    subject TEXT,
    snippet TEXT,
    body_text TEXT,
    provider_uid TEXT,
    provider_message_id TEXT,
    classification TEXT NOT NULL DEFAULT 'reply',
    received_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(sender_id, provider_uid)
);
CREATE INDEX IF NOT EXISTS idx_inbound_replies_user_received ON inbound_replies(user_id, received_at);
CREATE INDEX IF NOT EXISTS idx_inbound_replies_campaign ON inbound_replies(campaign_id, received_at);
CREATE INDEX IF NOT EXISTS idx_inbound_replies_from ON inbound_replies(user_id, from_email);
