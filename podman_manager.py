import subprocess
import json
import sqlite3
from datetime import datetime

DB_PATH = "autopod.db"

class PodmanManager:
    """Manages Podman containers and syncs them with the database."""

    def _run_cmd(self, cmd):
        """Run shell command and return JSON output."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running command {cmd}: {e.stderr}")
            return ""

    def get_containers(self):
        """Return a list of containers as JSON objects."""
        output = self._run_cmd(["podman", "ps", "-a", "--format", "json"])
        if not output:
            return []
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return []

    def get_logs(self, container_id):
        """Fetch logs for a specific container."""
        logs = self._run_cmd(["podman", "logs", "--tail", "50", container_id])
        return logs

    def sync_with_db(self):
        """Fetch Podman container data and store it in SQLite DB."""
        containers = self.get_containers()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS containers (
                id TEXT PRIMARY KEY,
                name TEXT,
                image TEXT,
                status TEXT,
                created TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                container_id TEXT,
                log TEXT,
                timestamp TEXT
            )
        """)

        cur.execute("DELETE FROM containers")
        cur.execute("DELETE FROM logs")

        for c in containers:
            cur.execute("""
                INSERT OR REPLACE INTO containers (id, name, image, status, created)
                VALUES (?, ?, ?, ?, ?)
            """, (
                c.get("Id", "")[:12],
                c.get("Names", ["unknown"])[0],
                c.get("Image", "unknown"),
                c.get("Status", "unknown"),
                c.get("CreatedAt", "")
            ))

            log_text = self.get_logs(c.get("Id", ""))
            cur.execute("""
                INSERT INTO logs (container_id, log, timestamp)
                VALUES (?, ?, ?)
            """, (
                c.get("Id", "")[:12],
                log_text,
                datetime.now().isoformat()
            ))

        conn.commit()
        conn.close()
        print(f"✅ Synced {len(containers)} containers with database.")
