CREATE TABLE IF NOT EXISTS email_templates (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Custom',
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_email_templates_user ON email_templates(user_id, updated_at);

CREATE TABLE IF NOT EXISTS sender_connections (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'gmail',
    email TEXT NOT NULL,
    display_name TEXT,
    credentials_ciphertext TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'connected',
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, provider, email)
);
CREATE INDEX IF NOT EXISTS idx_sender_connections_user ON sender_connections(user_id, status);

CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    template_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    daily_limit INTEGER NOT NULL DEFAULT 30,
    send_start_hour INTEGER NOT NULL DEFAULT 9,
    send_end_hour INTEGER NOT NULL DEFAULT 17,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    min_interval_seconds INTEGER NOT NULL DEFAULT 60,
    recipient_count INTEGER NOT NULL DEFAULT 0,
    sent_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    approved_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_campaigns_user_created ON campaigns(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status, updated_at);

CREATE TABLE IF NOT EXISTS email_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    scheduled_at TEXT,
    sent_at TEXT,
    provider_message_id TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(campaign_id, lead_id)
);
CREATE INDEX IF NOT EXISTS idx_email_messages_queue ON email_messages(status, scheduled_at, created_at);
CREATE INDEX IF NOT EXISTS idx_email_messages_campaign ON email_messages(campaign_id, status);
CREATE INDEX IF NOT EXISTS idx_email_messages_sender_sent ON email_messages(sender_id, sent_at);

CREATE TABLE IF NOT EXISTS suppression_entries (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    email TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL,
    UNIQUE(user_id, email)
);
CREATE INDEX IF NOT EXISTS idx_suppression_user ON suppression_entries(user_id, email);
