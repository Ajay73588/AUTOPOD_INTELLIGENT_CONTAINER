import os
import sqlite3
from typing import List, Dict

DB_FILE = os.path.join(os.path.dirname(__file__), 'autopod.db')


def _connect():
    return sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)


def _get_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def _ensure_tables_and_columns():
    conn = _connect()
    cur = conn.cursor()

    # Create tables if missing (minimal expected schema)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS containers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        container_name TEXT,
        status TEXT,
        created_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        container_name TEXT,
        container_id INTEGER,
        log TEXT,
        timestamp TEXT
    )
    """)
    conn.commit()

    # Ensure expected columns exist (SQLite supports ADD COLUMN)
    existing = _get_columns(conn, 'containers')
    if 'container_name' not in existing:
        cur.execute("ALTER TABLE containers ADD COLUMN container_name TEXT")
    if 'status' not in existing:
        cur.execute("ALTER TABLE containers ADD COLUMN status TEXT")
    if 'created_at' not in existing:
        cur.execute("ALTER TABLE containers ADD COLUMN created_at TEXT")

    existing_logs = _get_columns(conn, 'logs')
    if 'container_name' not in existing_logs:
        cur.execute("ALTER TABLE logs ADD COLUMN container_name TEXT")
    if 'container_id' not in existing_logs:
        cur.execute("ALTER TABLE logs ADD COLUMN container_id INTEGER")
    if 'log' not in existing_logs:
        cur.execute("ALTER TABLE logs ADD COLUMN log TEXT")
    if 'timestamp' not in existing_logs:
        cur.execute("ALTER TABLE logs ADD COLUMN timestamp TEXT")

    conn.commit()
    conn.close()


def init_db():
    """Initialize DB and ensure schema is compatible."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    _ensure_tables_and_columns()


def get_container_status() -> List[Dict]:
    """Return list of containers with keys: container_name, status, created_at."""
    conn = _connect()
    cur = conn.cursor()
    try:
        cols = _get_columns(conn, 'containers')
        # pick best column names available, fallback to NULL
        name_col = 'container_name' if 'container_name' in cols else ('name' if 'name' in cols else None)
        status_col = 'status' if 'status' in cols else ('state' if 'state' in cols else None)
        created_col = 'created_at' if 'created_at' in cols else ('created' if 'created' in cols else None)

        select_parts = []
        select_parts.append(f"{name_col} as container_name" if name_col else "NULL as container_name")
        select_parts.append(f"{status_col} as status" if status_col else "NULL as status")
        select_parts.append(f"{created_col} as created_at" if created_col else "NULL as created_at")

        sql = f"SELECT {', '.join(select_parts)} FROM containers"
        cur.execute(sql)
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "container_name": r[0],
                "status": r[1],
                "created_at": r[2]
            })
        return result
    finally:
        conn.close()


def get_container_logs(limit: int = 200) -> List[Dict]:
    """
    Return recent logs as list of dicts:
      { "container_name": <str|None>, "log": <str>, "timestamp": <str> }
    Handles missing container_name in logs by joining to containers if possible.
    """
    conn = _connect()
    cur = conn.cursor()
    try:
        log_cols = _get_columns(conn, 'logs')
        cont_cols = _get_columns(conn, 'containers')

        if 'container_name' in log_cols:
            sql = f"SELECT container_name, log, timestamp FROM logs ORDER BY timestamp DESC LIMIT ?"
            cur.execute(sql, (limit,))
        elif 'container_id' in log_cols and ('container_name' in cont_cols or 'name' in cont_cols):
            # join by container_id -> containers.id
            name_col = 'container_name' if 'container_name' in cont_cols else 'name'
            sql = f"""
                SELECT c.{name_col} as container_name, l.log, l.timestamp
                FROM logs l
                LEFT JOIN containers c ON l.container_id = c.id
                ORDER BY l.timestamp DESC
                LIMIT ?
            """
            cur.execute(sql, (limit,))
        else:
            # fallback: return logs without container name
            sql = f"SELECT NULL as container_name, log, timestamp FROM logs ORDER BY timestamp DESC LIMIT ?"
            cur.execute(sql, (limit,))

        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "container_name": r[0],
                "log": r[1],
                "timestamp": r[2]
            })
        return result
    finally:
        conn.close()


def close_db_connection():
    """
    Placeholder/compatibility function to satisfy callers (e.g. atexit cleanup).
    This module opens and closes connections per-call, so there's no persistent
    connection to close. If you later change to a persistent connection, update
    this function to close it.
    """
    # no-op for current implementation
    return
