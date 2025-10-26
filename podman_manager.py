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
        """Return a list of containers as JSON objects."""
        try:
            cmd = ["podman", "ps", "-a", "--format", "json"]
            print(f"Running Podman command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not result.stdout.strip():
                print("No output from Podman command")
                return []
                
            containers = json.loads(result.stdout)
            print(f"Podman returned {len(containers)} containers")
            
            # Debug: print container names and statuses
            for container in containers:
                name = container.get("Names", ["unknown"])[0] if container.get("Names") else "unknown"
                status = container.get("Status", "unknown")
                state = container.get("State", "unknown")
                print(f"  - {name}: {status} (State: {state})")
                
            return containers
            
        except subprocess.CalledProcessError as e:
            print(f"Podman command failed. Error: {e.stderr}")
            return []
        except json.JSONDecodeError as e:
            print(f"Failed to parse Podman JSON. Error: {e}")
            print(f"Raw output: {result.stdout}")
            return []

    def get_logs(self, container_id_or_name):
        """Fetch logs for a specific Podman container."""
        try:
            logs = self._run_cmd(["podman", "logs", "--tail", "50", container_id_or_name])
            return logs
        except Exception as e:
            print(f"Error getting logs for {container_id_or_name}: {e}")
            return f"Error fetching logs: {str(e)}"

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
                    container_state = container.get("State", "unknown")

                    # Clean up container name if it's a list
                    if isinstance(container_name, list):
                        container_name = container_name[0] if container_name else "unknown"
                    
                    # Fix the "292 years ago" timestamp issue and normalize status
                    if "292 years ago" in container_status:
                        if container_state == "running":
                            container_status = "Running"
                        else:
                            container_status = "Exited"
                    elif "Exited" in container_status:
                        container_status = "Exited"
                    elif "Up" in container_status:
                        container_status = "Running"
                    elif "Created" in container_status:
                        container_status = "Created"
                    
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

                    # Get and insert logs (only for running containers to avoid errors)
                    try:
                        if container_state == "running":
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
                        else:
                            # For stopped containers, add a status message
                            cur.execute("""
                                INSERT INTO logs (container_name, log, timestamp)
                                VALUES (?, ?, ?)
                            """, (
                                container_name,
                                f"Container is {container_status}. Start container to see logs.",
                                datetime.now().isoformat()
                            ))
                    except Exception as e:
                        print(f"Error getting logs for {container_name}: {e}")
                        # Add error to logs
                        cur.execute("""
                            INSERT INTO logs (container_name, log, timestamp)
                            VALUES (?, ?, ?)
                        """, (
                            container_name,
                            f"Error fetching logs: {str(e)}",
                            datetime.now().isoformat()
                        ))
                        
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

    def start_container(self, container_name):
        """Start a stopped Podman container."""
        try:
            self._run_cmd(["podman", "start", container_name])
            print(f"✅ Container started: {container_name}")
            return True
        except Exception as e:
            print(f"❌ Error starting container {container_name}: {e}")
            return False

    # ========== HEALTH MONITORING METHODS ==========

    def get_container_stats(self, container_name):
        """Get real-time container statistics with better parsing."""
        try:
            output = self._run_cmd([
                "podman", "stats", container_name, 
                "--no-stream", "--format", "json"
            ])
            if output:
                stats_data = json.loads(output)
                if isinstance(stats_data, list) and stats_data:
                    stats = stats_data[0]
                    
                    # Parse CPU percentage
                    cpu_percent = stats.get('CPU', '0%')
                    if cpu_percent == '--':
                        cpu_percent = '0%'
                    
                    # Parse memory usage
                    mem_usage = stats.get('MemUsage', '0B / 0B')
                    if ' / ' in mem_usage:
                        mem_used, mem_limit = mem_usage.split(' / ')
                    else:
                        mem_used, mem_limit = '0B', 'N/A'
                    
                    # Parse network I/O
                    net_io = stats.get('NetIO', '0B / 0B')
                    if net_io == '-- / --':
                        net_io = '0B / 0B'
                    
                    # Parse block I/O
                    block_io = stats.get('BlockIO', '0B / 0B')
                    if block_io == '-- / --':
                        block_io = '0B / 0B'
                    
                    # Parse PIDs
                    pids = stats.get('PIDs', '0')
                    if pids == '--':
                        pids = '0'
                    
                    return {
                        'cpu_percent': cpu_percent,
                        'memory_used': mem_used.strip(),
                        'memory_limit': mem_limit.strip(),
                        'network_io': net_io,
                        'block_io': block_io,
                        'pids': pids,
                        'container_name': stats.get('Name', container_name)
                    }
            return {
                'cpu_percent': '0%',
                'memory_used': '0B',
                'memory_limit': 'N/A',
                'network_io': '0B / 0B',
                'block_io': '0B / 0B',
                'pids': '0',
                'container_name': container_name
            }
        except Exception as e:
            print(f"Error getting stats for {container_name}: {e}")
            return {
                'cpu_percent': '0%',
                'memory_used': '0B',
                'memory_limit': 'N/A',
                'network_io': '0B / 0B',
                'block_io': '0B / 0B',
                'pids': '0',
                'container_name': container_name
            }

    def get_container_health(self, container_name):
        """Check container health status with fallback logic."""
        try:
            # Get detailed container info
            output = self._run_cmd([
                "podman", "inspect", container_name, "--format", "json"
            ])
            if output:
                container_info = json.loads(output)
                if isinstance(container_info, list) and container_info:
                    container_data = container_info[0]
                    
                    # Check health status from container inspect
                    state = container_data.get('State', {})
                    status = state.get('Status', 'unknown').lower()
                    
                    # If container has explicit health check, use it
                    health = state.get('Health', {})
                    health_status = health.get('Status', 'unknown')
                    
                    # If no explicit health check, infer from status
                    if health_status == 'unknown' or not health_status:
                        if status == 'running':
                            health_status = 'healthy'
                        elif status == 'exited':
                            health_status = 'exited'
                        elif status == 'created':
                            health_status = 'starting'
                        else:
                            health_status = status
                    
                    return {
                        'status': health_status,
                        'failures': health.get('FailingStreak', 0),
                        'log': health.get('Log', []),
                        'inferred': health_status != health.get('Status', 'unknown')
                    }
            return {'status': 'unknown', 'failures': 0, 'log': [], 'inferred': True}
        except Exception as e:
            print(f"Error checking health for {container_name}: {e}")
            return {'status': 'unknown', 'failures': 0, 'log': [], 'inferred': True}

    def get_container_resources(self, container_name):
        """Get container resource usage and limits with better data."""
        try:
            # Get real-time stats first
            stats = self.get_container_stats(container_name)
            
            # Get container info for additional data
            output = self._run_cmd([
                "podman", "inspect", container_name, "--format", "json"
            ])
            
            restart_count = 0
            created_date = 'unknown'
            
            if output:
                container_info = json.loads(output)
                if isinstance(container_info, list) and container_info:
                    container_data = container_info[0]
                    
                    # Get restart count
                    restart_count = container_data.get('RestartCount', 0)
                    
                    # Get proper created date
                    created = container_data.get('Created', '')
                    if created:
                        try:
                            # Convert ISO timestamp to readable format
                            created_date = datetime.fromisoformat(created.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            created_date = created
                    
                    # Get resource limits from HostConfig
                    host_config = container_data.get('HostConfig', {})
                    memory_limit = host_config.get('Memory', 0)
                    if memory_limit and memory_limit > 0:
                        # Convert bytes to human readable
                        stats['memory_limit'] = self._bytes_to_human(memory_limit)
            
            return {
                'cpu_percent': stats.get('cpu_percent', '0%'),
                'memory_usage': stats.get('memory_used', '0B'),
                'memory_limit': stats.get('memory_limit', 'N/A'),
                'network_io': stats.get('network_io', '0B / 0B'),
                'block_io': stats.get('block_io', '0B / 0B'),
                'pids': stats.get('pids', '0'),
                'restart_count': restart_count,
                'created_at': created_date,
                'container_name': container_name
            }
        except Exception as e:
            print(f"Error getting resources for {container_name}: {e}")
            return {
                'cpu_percent': '0%',
                'memory_usage': '0B',
                'memory_limit': 'N/A',
                'network_io': '0B / 0B',
                'block_io': '0B / 0B',
                'pids': '0',
                'restart_count': 0,
                'created_at': 'unknown',
                'container_name': container_name
            }

    def _bytes_to_human(self, bytes_size):
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f}TB"

    def get_all_containers_health(self):
        """Get health status for all containers."""
        containers = self.get_containers()
        health_data = {}
        
        for container in containers:
            container_name = container.get("Names", [""])[0] if container.get("Names") else "unknown"
            if isinstance(container_name, list):
                container_name = container_name[0]
                
            health_data[container_name] = {
                'health': self.get_container_health(container_name),
                'resources': self.get_container_resources(container_name),
                'basic_info': {
                    'status': container.get('Status', 'unknown'),
                    'state': container.get('State', 'unknown'),
                    'image': container.get('Image', 'unknown'),
                    'created': container.get('Created', 'unknown')
                }
            }
        
        return health_data