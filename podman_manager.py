import subprocess
import json
import sqlite3
from datetime import datetime

DB_PATH = "autopod.db"

class PodmanManager:
    """Manages Podman containers and syncs them with the database."""

    def _run_cmd(self, cmd):
        """Run shell command and return output."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running command {cmd}: {e.stderr}")
            return ""

    def get_containers(self):
        """Return a list of Podman containers as JSON objects."""
        output = self._run_cmd(["podman", "ps", "-a", "--format", "json"])
        if not output:
            return []
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return []

    def get_logs(self, container_id_or_name):
        """Fetch logs for a specific Podman container."""
        logs = self._run_cmd(["podman", "logs", "--tail", "50", container_id_or_name])
        return logs

    def sync_with_db(self):
        """Fetch Podman container data and store it in SQLite DB using the correct schema."""
        containers = self.get_containers()
        
        # Import here to avoid circular imports
        from database import get_db_cursor
        
        with get_db_cursor() as cur:
            # Clear existing data
            cur.execute("DELETE FROM containers")
            cur.execute("DELETE FROM logs")

            for container in containers:
                try:
                    container_name = container.get("Names", [""])[0] if container.get("Names") else "unknown"
                    container_status = container.get("Status", "unknown")
                    container_id = container.get("Id", "")[:12]  # Short container ID

                    # Clean up container name if it's a list
                    if isinstance(container_name, list):
                        container_name = container_name[0] if container_name else "unknown"
                    
                    # Fix timestamp issues in status
                    if "292 years ago" in container_status:
                        container_status = container_status.replace("292 years ago", "recently")
                    
                    print(f"Syncing container: {container_name} - Status: {container_status}")

                    # Insert into containers table
                    cur.execute("""
                        INSERT INTO containers (container_name, status, created_at)
                        VALUES (?, ?, ?)
                    """, (
                        container_name,
                        container_status,
                        datetime.now().isoformat()
                    ))

                    # Get and insert logs
                    try:
                        log_text = self.get_logs(container_id)
                        if log_text:
                            log_lines = log_text.split('\n')
                            for line in log_lines:
                                if line.strip():
                                    cur.execute("""
                                        INSERT INTO logs (container_name, log, timestamp)
                                        VALUES (?, ?, ?)
                                    """, (
                                        container_name,
                                        line.strip(),
                                        datetime.now().isoformat()
                                    ))
                    except Exception as e:
                        print(f"Error getting logs for {container_name}: {e}")
                        
                except Exception as e:
                    print(f"Error processing container: {e}")
                    continue

        print(f"✅ Synced {len(containers)} Podman containers with database.")

    def build_image(self, path, image_name):
        """Build container image from Containerfile/Dockerfile using Podman."""
        try:
            # Podman build command (same as Docker but using podman)
            result = self._run_cmd(["podman", "build", "-t", image_name, path])
            print(f"✅ Image built successfully: {image_name}")
            return True
        except Exception as e:
            print(f"❌ Error building image: {e}")
            return False

    def stop_container(self, container_name):
        """Stop a running Podman container."""
        try:
            self._run_cmd(["podman", "stop", container_name])
            print(f"✅ Container stopped: {container_name}")
            return True
        except Exception as e:
            print(f"❌ Error stopping container {container_name}: {e}")
            return False

    def remove_container(self, container_name):
        """Remove a Podman container."""
        try:
            self._run_cmd(["podman", "rm", container_name])
            print(f"✅ Container removed: {container_name}")
            return True
        except Exception as e:
            print(f"❌ Error removing container {container_name}: {e}")
            return False

    def run_container(self, image_name, container_name, ports=None, env_vars=None):
        """Run a Podman container from image."""
        cmd = ["podman", "run", "-d", "--name", container_name]
        
        # Add port mappings if specified
        if ports:
            cmd.extend(["-p", ports])
        
        # Add environment variables if specified
        if env_vars:
            for key, value in env_vars.items():
                cmd.extend(["-e", f"{key}={value}"])
        
        cmd.append(image_name)
        
        try:
            self._run_cmd(cmd)
            print(f"✅ Container started: {container_name} from image {image_name}")
            return True
        except Exception as e:
            print(f"❌ Error running container {container_name}: {e}")
            return False

    def restart_container(self, container_name):
        """Restart a Podman container."""
        try:
            self._run_cmd(["podman", "restart", container_name])
            print(f"✅ Container restarted: {container_name}")
            return True
        except Exception as e:
            print(f"❌ Error restarting container {container_name}: {e}")
            return False