CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    section TEXT NOT NULL,
    file_path TEXT NOT NULL,
    title TEXT NOT NULL,
    created TEXT NOT NULL,
    updated TEXT NOT NULL,
    confidence REAL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'wikilink',
    weight REAL DEFAULT 1.0,
    auto_discovered INTEGER DEFAULT 1,
    UNIQUE(source_id, target_id, relationship_type)
);

CREATE TABLE IF NOT EXISTS provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    date TEXT NOT NULL,
    verified_by TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS search_index (
    node_id TEXT NOT NULL,
    keywords TEXT NOT NULL,
    PRIMARY KEY (node_id)
);
