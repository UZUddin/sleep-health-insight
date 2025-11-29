# backend/db.py
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "sleep.db"

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS heart_rate (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,             -- epoch ms (UTC)
  value REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hr_ts_id ON heart_rate(ts, id);

CREATE TABLE IF NOT EXISTS sleep_epoch (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  start_ts INTEGER NOT NULL,       -- epoch ms (UTC)
  end_ts INTEGER NOT NULL,         -- epoch ms (UTC)
  stage TEXT                       -- "ASLEEP"|"INBED"|"AWARENESS"|"REM" (if present)
);

CREATE INDEX IF NOT EXISTS idx_sleep_start ON sleep_epoch(start_ts);
"""

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
