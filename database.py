import sqlite3
import threading
from contextlib import contextmanager

DB_NAME = "autopod.db"

# Use thread-local storage for database connections
thread_local = threading.local()

def get_db_connection():
    """Get a database connection for the current thread."""
    if not hasattr(thread_local, 'connection'):
        thread_local.connection = sqlite3.connect(DB_NAME, timeout=30.0)
        thread_local.connection.row_factory = sqlite3.Row
    return thread_local.connection

@contextmanager
def get_db_cursor():
    """Context manager for database operations with proper error handling."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()

def init_db():
    """Initialize the database tables."""
    with get_db_cursor() as cursor:
        # Create containers table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS containers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_name TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create logs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_name TEXT,
            log TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

def get_container_status():
    """Get container statuses from database."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT container_name, status, created_at FROM containers ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [{"container_name": r[0], "status": r[1], "created_at": r[2]} for r in rows]

def get_container_logs():
    """Get container logs from database."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT container_name, log, timestamp FROM logs ORDER BY timestamp DESC LIMIT 100")
        rows = cursor.fetchall()
        return [{"container_name": r[0], "log": r[1], "timestamp": r[2]} for r in rows]

def close_db_connection():
    """Close the database connection for the current thread."""
    if hasattr(thread_local, 'connection'):
        thread_local.connection.close()
        del thread_local.connection