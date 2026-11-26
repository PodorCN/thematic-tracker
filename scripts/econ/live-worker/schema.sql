CREATE TABLE IF NOT EXISTS calendar_schedule (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  checked_at INTEGER NOT NULL,
  events TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calendar_releases (
  id TEXT PRIMARY KEY,
  release_at INTEGER NOT NULL,
  checked_at INTEGER NOT NULL,
  details TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS calendar_releases_by_date ON calendar_releases (release_at);
