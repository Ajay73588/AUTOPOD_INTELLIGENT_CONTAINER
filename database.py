import sqlite3
import json

def init_db():
    """Initialize SQLite database."""
    conn = sqlite3.connect('autopod.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS containers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            image TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_name TEXT,
            log_message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_container_action(container_name, action):
    """Log container actions to database."""
    conn = sqlite3.connect('autopod.db')
    c = conn.cursor()
    c.execute("INSERT INTO logs (container_name, log_message) VALUES (?, ?)", 
              (container_name, json.dumps(action)))
    conn.commit()
    conn.close()

def get_container_logs():
    """Retrieve container logs from database."""
    conn = sqlite3.connect('autopod.db')
    c = conn.cursor()
    c.execute("SELECT container_name, log_message, timestamp FROM logs ORDER BY timestamp DESC")
    logs = [{"container": row[0], "message": json.loads(row[1]), "timestamp": row[2]} for row in c.fetchall()]
    conn.close()
    return logs

def get_container_status():
    """Retrieve container statuses from database."""
    conn = sqlite3.connect('autopod.db')
    c = conn.cursor()
    c.execute("SELECT name, image, status, created_at FROM containers")
    statuses = [{"name": row[0], "image": row[1], "status": row[2], "created_at": row[3]} for row in c.fetchall()]
    conn.close()
    return statuses