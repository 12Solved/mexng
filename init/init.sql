CREATE TYPE run_state AS ENUM ('running', 'success', 'failed', 'skipped', 're_run');
CREATE TYPE log_level AS ENUM (
    'DEBUG',
    'INFO',
    'WARNING',
    'ERROR',
    'CRITICAL'
);

CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    message_id TEXT,
    subject TEXT,
    sender TEXT,
    recipient TEXT,
    date TIMESTAMP,
    body TEXT,
    html_body TEXT,
    raw_headers JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_email_message_id ON emails(message_id);

CREATE TABLE mailbox_state (
    id SERIAL PRIMARY KEY,
    email_account TEXT NOT NULL,
    mailbox TEXT NOT NULL DEFAULT 'INBOX',
    uidvalidity TEXT,
    last_seen_uid TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(email_account, mailbox)
);

CREATE TABLE attachments (
    id SERIAL PRIMARY KEY,
    email_id INTEGER NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    content_type TEXT,
    size INTEGER,
    content BYTEA,
    storage_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE workflows (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    workflow_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    enabled BOOLEAN DEFAULT TRUE
);

CREATE TABLE runs (
    id SERIAL PRIMARY KEY,
    workflow_id INTEGER REFERENCES workflows(id) ON DELETE SET NULL,
    email_id INTEGER REFERENCES emails(id) ON DELETE SET NULL,
    state run_state NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parent_run_id INTEGER REFERENCES runs(id) ON DELETE SET NULL,
    attempt INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE logs (
    id SERIAL PRIMARY KEY,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    level log_level NOT NULL,
    event_type TEXT NOT NULL,

    message TEXT,
    step TEXT,

    email_id INTEGER REFERENCES emails(id) ON DELETE SET NULL,
    workflow_id INTEGER REFERENCES workflows(id) ON DELETE SET NULL,
    attachment_id INTEGER REFERENCES attachments(id) ON DELETE SET NULL,
    run_id INTEGER REFERENCES runs(id) ON DELETE SET NULL
);

CREATE TABLE checkpoints (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    reference_timestamp TIMESTAMP NOT NULL,
    normal_interval_hours INTEGER NOT NULL,
    late_interval_hours INTEGER,
    next_expected_at TIMESTAMP NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    last_successful TIMESTAMP,
    last_missed TIMESTAMP,
    last_seen_at TIMESTAMP,
    status VARCHAR NOT NULL DEFAULT 'never_seen' CHECK (status IN ('ok', 'missed', 'never_seen')),
    workflow_id INTEGER REFERENCES workflows(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
