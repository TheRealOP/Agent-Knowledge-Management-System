CREATE TABLE IF NOT EXISTS checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_type TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    messages_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_home_state INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS forks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checkpoint_id INTEGER NOT NULL,
    fork_messages_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_agent ON checkpoints(agent_id, is_home_state);
