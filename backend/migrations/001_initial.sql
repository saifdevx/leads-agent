CREATE TABLE IF NOT EXISTS users (
    firebase_uid TEXT PRIMARY KEY,
    email TEXT,
    display_name TEXT,
    email_verified INTEGER NOT NULL DEFAULT 0,
    sign_in_provider TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_login_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS lead_lists (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    niche TEXT NOT NULL,
    location TEXT,
    target_count INTEGER NOT NULL DEFAULT 100,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lead_lists_user_created
    ON lead_lists(user_id, created_at);

CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    list_id TEXT NOT NULL,
    company_name TEXT,
    website TEXT,
    domain TEXT,
    first_name TEXT,
    last_name TEXT,
    job_title TEXT,
    email TEXT,
    email_status TEXT,
    phone TEXT,
    linkedin_url TEXT,
    instagram_url TEXT,
    facebook_url TEXT,
    city TEXT,
    region TEXT,
    country TEXT,
    source TEXT,
    source_url TEXT,
    source_query TEXT,
    score REAL,
    status TEXT NOT NULL DEFAULT 'discovered',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_leads_user_list
    ON leads(user_id, list_id);
CREATE INDEX IF NOT EXISTS idx_leads_user_email
    ON leads(user_id, email);
CREATE INDEX IF NOT EXISTS idx_leads_user_status
    ON leads(user_id, status);

CREATE TABLE IF NOT EXISTS provider_connections (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    credentials_ciphertext TEXT,
    status TEXT NOT NULL DEFAULT 'disconnected',
    last_validated_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_provider_connections_user
    ON provider_connections(user_id);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 100,
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT,
    run_after TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_run_after
    ON jobs(status, run_after, priority);
CREATE INDEX IF NOT EXISTS idx_jobs_user_created
    ON jobs(user_id, created_at);
