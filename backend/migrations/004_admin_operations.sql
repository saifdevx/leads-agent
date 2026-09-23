ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user';
CREATE INDEX IF NOT EXISTS idx_users_status_role ON users(status, role);

ALTER TABLE jobs ADD COLUMN locked_at TEXT;
ALTER TABLE jobs ADD COLUMN locked_by TEXT;
CREATE INDEX IF NOT EXISTS idx_jobs_worker_claim ON jobs(status, job_type, run_after, priority, created_at);

ALTER TABLE sender_connections ADD COLUMN webhook_status TEXT NOT NULL DEFAULT 'not_configured';
ALTER TABLE sender_connections ADD COLUMN webhook_url TEXT;

CREATE TABLE IF NOT EXISTS worker_heartbeats (
    worker_name TEXT PRIMARY KEY,
    instance_id TEXT,
    last_seen_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS admin_audit_log (
    id TEXT PRIMARY KEY,
    actor_user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_created ON admin_audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_admin_audit_actor ON admin_audit_log(actor_user_id, created_at);
