import subprocess
import json
import sqlite3
from datetime import datetime
import os

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
        """Build a Podman image from a Containerfile or Dockerfile with real-time output."""
        try:
            # First check if Containerfile exists (Podman default)
            containerfile_path = os.path.join(path, "Containerfile")
            dockerfile_path = os.path.join(path, "Dockerfile")
            
            build_cmd = ["podman", "build", "-t", image_name]
            
            if os.path.exists(containerfile_path):
                # Use Containerfile (Podman default)
                build_cmd.extend(["-f", "Containerfile", path])
                print(f"🔨 [DEBUG] Building with Containerfile from: {path}")
            elif os.path.exists(dockerfile_path):
                # Use Dockerfile (Docker compatible)
                build_cmd.extend(["-f", "Dockerfile", path])
                print(f"🔨 [DEBUG] Building with Dockerfile from: {path}")
            else:
                print(f"❌ [DEBUG] No Containerfile or Dockerfile found in: {path}")
                return False
            
            print(f"🔨 [DEBUG] Build command: {' '.join(build_cmd)}")
            
            # Run build command with output streaming
            process = subprocess.Popen(
                build_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=path
            )
            
            # Stream build output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(f"🔨 [BUILD] {output.strip()}")
            
            return_code = process.poll()
            
            if return_code == 0:
                print(f"✅ [DEBUG] Image built successfully: {image_name}")
                return True
            else:
                print(f"❌ [DEBUG] Image build failed with return code: {return_code}")
                return False
                
        except Exception as e:
            print(f"❌ [DEBUG] Error building image: {e}")
            return False

    def start_container(self, container_name):
        """Start a stopped Podman container with better error handling."""
        try:
            print(f"🚀 Starting container: {container_name}")
            
            # First, try to find the exact container name or ID
            containers = self.get_containers()
            actual_container_name = None
            container_id = None
            
            for container in containers:
                container_names = container.get("Names", [])
                current_container_id = container.get("Id", "")
                
                # Check if any name matches
                for name in container_names:
                    if container_name in name or name in container_name:
                        actual_container_name = name
                        container_id = current_container_id
                        break
                
                # Also check container ID
                if current_container_id.startswith(container_name):
                    actual_container_name = current_container_id
                    container_id = current_container_id
                    break
            
            # Use the found name or original name
            target_name = actual_container_name or container_name
            print(f"🔍 Found container to start: {target_name}")
            
            # Start the container
            result = self._run_cmd(["podman", "start", target_name])
            
            if "Error" in result or "error" in result.lower():
                print(f"❌ Error starting container {target_name}: {result}")
                return False
            
            print(f"✅ Container started successfully: {target_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error starting container {container_name}: {e}")
            return False

    def stop_container(self, container_name):
        """Stop a running Podman container."""
        try:
            print(f"🛑 Stopping container: {container_name}")
            
            # Find the exact container
            containers = self.get_containers()
            actual_container_name = None
            
            for container in containers:
                container_names = container.get("Names", [])
                container_id = container.get("Id", "")
                
                for name in container_names:
                    if container_name in name or name in container_name:
                        actual_container_name = name
                        break
                
                if container_id.startswith(container_name):
                    actual_container_name = container_id
                    break
            
            target_name = actual_container_name or container_name
            print(f"🔍 Found container to stop: {target_name}")
            
            result = self._run_cmd(["podman", "stop", target_name])
            
            if "Error" in result or "error" in result.lower():
                print(f"❌ Error stopping container {target_name}: {result}")
                return False
            
            print(f"✅ Container stopped successfully: {target_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping container {container_name}: {e}")
            return False

    def restart_container(self, container_name):
        """Restart a Podman container."""
        try:
            print(f"🔄 Restarting container: {container_name}")
            
            # Find the exact container
            containers = self.get_containers()
            actual_container_name = None
            
            for container in containers:
                container_names = container.get("Names", [])
                container_id = container.get("Id", "")
                
                for name in container_names:
                    if container_name in name or name in container_name:
                        actual_container_name = name
                        break
                
                if container_id.startswith(container_name):
                    actual_container_name = container_id
                    break
            
            target_name = actual_container_name or container_name
            print(f"🔍 Found container to restart: {target_name}")
            
            result = self._run_cmd(["podman", "restart", target_name])
            
            if "Error" in result or "error" in result.lower():
                print(f"❌ Error restarting container {target_name}: {result}")
                return False
            
            print(f"✅ Container restarted successfully: {target_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error restarting container {container_name}: {e}")
            return False

    def remove_container(self, container_name):
        """Remove a Podman container."""
        try:
            print(f"🗑 Removing container: {container_name}")
            
            # Find the exact container
            containers = self.get_containers()
            actual_container_name = None
            
            for container in containers:
                container_names = container.get("Names", [])
                container_id = container.get("Id", "")
                
                for name in container_names:
                    if container_name in name or name in container_name:
                        actual_container_name = name
                        break
                
                if container_id.startswith(container_name):
                    actual_container_name = container_id
                    break
            
            target_name = actual_container_name or container_name
            print(f"🔍 Found container to remove: {target_name}")
            
            # First stop the container if it's running
            self._run_cmd(["podman", "stop", target_name])
            
            # Then remove it
            result = self._run_cmd(["podman", "rm", target_name])
            
            if "Error" in result or "error" in result.lower():
                print(f"❌ Error removing container {target_name}: {result}")
                return False
            
            print(f"✅ Container removed successfully: {target_name}")
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

    def push_image(self, image_name, registry="docker.io", username=None):
    
        try:
            print(f"🚀 Starting push process for: {image_name}")
            print(f"📦 Registry: {registry}, Username: {username}")
            
            # First, check if the image exists locally - handle various formats
            images = self.get_images()
            image_exists = False
            original_image_name = None
            
            for img in images:
                repo = img.get('Repository', '')
                if not repo or repo == '<none>':
                    continue
                    
                # Check various possible matches
                clean_repo = self._clean_image_name(repo)
                clean_input = self._clean_image_name(image_name)
                
                print(f"🔍 Checking: {repo} -> {clean_repo} vs input: {image_name} -> {clean_input}")
                
                # Match by clean name (without localhost/ and tags)
                if clean_repo == clean_input:
                    image_exists = True
                    original_image_name = repo
                    break
                # Also check direct match
                elif repo == image_name:
                    image_exists = True
                    original_image_name = repo
                    break
                # Check if input matches any name in Names array
                elif img.get('Names'):
                    for name in img.get('Names', []):
                        if self._clean_image_name(name) == clean_input:
                            image_exists = True
                            original_image_name = name
                            break
                    if image_exists:
                        break
            
            if not image_exists:
                print(f"❌ Image {image_name} not found locally. Available images:")
                for img in images:
                    repo = img.get('Repository', '')
                    if repo and repo != '<none>':
                        print(f"   - {repo}")
                return False
            
            print(f"✅ Found image: {original_image_name}")
            
            # Get clean name for tagging (without localhost/ and tags)
            clean_name = self._clean_image_name(original_image_name)
            
            # Tag the image for the registry
            if registry == "docker.io":
                if username:
                    tagged_name = f"docker.io/{username}/{clean_name}:latest"
                    registry_url = f"https://hub.docker.com/r/{username}/{clean_name}"
                else:
                    tagged_name = f"docker.io/{clean_name}:latest"
                    registry_url = f"https://hub.docker.com/r/{clean_name}"
            elif registry == "quay.io":
                tagged_name = f"quay.io/{username}/{clean_name}:latest" if username else f"quay.io/{clean_name}:latest"
                registry_url = f"https://quay.io/repository/{username}/{clean_name}" if username else f"https://quay.io/repository/{clean_name}"
            elif registry == "ghcr.io":
                tagged_name = f"ghcr.io/{username}/{clean_name}:latest" if username else f"ghcr.io/{clean_name}:latest"
                registry_url = f"https://github.com/users/{username}/packages/container/package/{clean_name}" if username else f"https://github.com/users/{username}/packages"
            else:
                tagged_name = f"{registry}/{clean_name}:latest"
                registry_url = f"https://{registry}/{clean_name}"
            
            print(f"🏷 Tagging {original_image_name} as: {tagged_name}")
            
            # Tag the image using the original name
            tag_cmd = ["podman", "tag", original_image_name, tagged_name]
            tag_result = self._run_cmd(tag_cmd)
            
            if "Error" in tag_result or "error" in tag_result.lower():
                print(f"❌ Error tagging image: {tag_result}")
                return False
            
            print(f"✅ Image tagged successfully: {tagged_name}")
            
            # Push the image
            print(f"📤 Pushing image to registry...")
            push_cmd = ["podman", "push", tagged_name]
            push_result = self._run_cmd(push_cmd)
            
            if "Error" in push_result or "error" in push_result.lower():
                print(f"❌ Error pushing image: {push_result}")
                return False
            
            print(f"✅ Image pushed successfully: {tagged_name}")
            
            return {
                "success": True,
                "message": f"Image {clean_name} pushed successfully to {registry}",
                "tagged_name": tagged_name,
                "registry_url": registry_url,
                "pull_command": f"podman pull {tagged_name}"
            }
            
        except Exception as e:
            print(f"❌ Error pushing image: {e}")
            return False

    def _clean_image_name(self, image_name):
        """Clean image name by removing registry and tag."""
        if not image_name:
            return ""
        
        clean_name = image_name
        
        # Remove registry prefix (everything before last '/')
        if '/' in clean_name:
            clean_name = clean_name.split('/')[-1]
        
        # Remove tag (everything after ':')
        if ':' in clean_name:
            clean_name = clean_name.split(':')[0]
        
        return clean_name
    def get_pushable_images(self):  # Fixed: Added colon and self parameter
        """Get list of images that can be pushed to registry."""
        try:
            images = self.get_images()
            pushable_images = []
            
            for image in images:
                repo = image.get('Repository', '')
                tag = image.get('Tag', 'latest')
                image_id = image.get('Id', '')[:12]
                size = image.get('Size', '0B')
                created = image.get('Created', 'unknown')
                
                # Skip intermediate/images without proper repository
                if repo and repo != '<none>':
                    # Handle localhost/ prefix
                    if repo.startswith('localhost/'):
                        clean_name = repo.replace('localhost/', '')
                        pushable_images.append({
                            'repository': clean_name,
                            'tag': tag,
                            'image_id': image_id,
                            'size': size,
                            'created': created,
                            'full_name': f"{clean_name}:{tag}",
                            'is_local': True,
                            'original_name': repo  # Keep original for reference
                        })
                    else:
                        # Regular images (not localhost)
                        pushable_images.append({
                            'repository': repo,
                            'tag': tag,
                            'image_id': image_id,
                            'size': size,
                            'created': created,
                            'full_name': f"{repo}:{tag}",
                            'is_local': False
                        })
            
            return pushable_images
        except Exception as e:
            print(f"Error getting pushable images: {e}")
            return []
        
        

    

    def check_docker_login(self):  # Fixed: Proper indentation
        """Check if user is logged in to Docker Hub."""
        try:
            result = self._run_cmd(["podman", "login", "--get-login", "docker.io"])
            return bool(result and "not logged in" not in result.lower())
        except Exception as e:
            print(f"Error checking Docker login: {e}")
            return False

    # ... (rest of your existing methods remain the same)

    # ... (rest of your existing methods remain the same)

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
    
    def get_container_ports(self, container_name):
        """Get the port mappings for a container."""
        try:
            # Get port mappings from container inspect
            output = self._run_cmd([
                "podman", "inspect", container_name, 
                "--format", "json"
            ])
            
            if output:
                container_info = json.loads(output)
                if isinstance(container_info, list) and container_info:
                    container_data = container_info[0]
                    
                    # Get network settings
                    network_settings = container_data.get('NetworkSettings', {})
                    ports = network_settings.get('Ports', {})
                    
                    # Get host config ports
                    host_config = container_data.get('HostConfig', {})
                    port_bindings = host_config.get('PortBindings', {})
                    
                    # Parse port mappings
                    port_mappings = []
                    
                    if ports:
                        for container_port, host_ports in ports.items():
                            if host_ports and isinstance(host_ports, list):
                                for host_mapping in host_ports:
                                    if host_mapping:
                                        host_port = host_mapping.get('HostPort', '')
                                        host_ip = host_mapping.get('HostIp', '0.0.0.0')
                                        if host_port:
                                            port_mappings.append({
                                                'container_port': container_port,
                                                'host_port': host_port,
                                                'host_ip': host_ip,
                                                'url': f"http://{host_ip}:{host_port}" if host_ip != '0.0.0.0' else f"http://127.0.0.1:{host_port}"
                                            })
                    
                    # Alternative method: check published ports
                    if not port_mappings and port_bindings:
                        for container_port, bindings in port_bindings.items():
                            if bindings and isinstance(bindings, list):
                                for binding in bindings:
                                    host_port = binding.get('HostPort', '')
                                    if host_port:
                                        port_mappings.append({
                                            'container_port': container_port,
                                            'host_port': host_port,
                                            'host_ip': '127.0.0.1',
                                            'url': f"http://127.0.0.1:{host_port}"
                                        })
                    
                    return port_mappings
                    
            return []
            
        except Exception as e:
            print(f"Error getting ports for {container_name}: {e}")
            return []

    def get_container_web_url(self, container_name):
        """Get the primary web URL for a container (HTTP port 80/8080/3000 etc.)."""
        ports = self.get_container_ports(container_name)
        
        if not ports:
            return None
        
        # Prioritize common web ports
        web_port_priority = ['80', '8080', '3000', '5000', '8000', '8081', '4200', '3001']
        
        for priority_port in web_port_priority:
            for port_mapping in ports:
                if port_mapping['container_port'].startswith(priority_port + '/'):
                    return port_mapping['url']
        
        # If no common web ports, return the first available port
        return ports[0]['url'] if ports else None

    def get_container_status_for_ui(self, container_name):
        """Get enhanced container status including web URL for UI."""
        basic_info = {
            'name': container_name,
            'web_url': None,
            'has_web_interface': False,
            'ports': []
        }
        
        # Check if container is running
        status_cmd = ["podman", "inspect", container_name, "--format", "{{.State.Status}}"]
        status = self._run_cmd(status_cmd).strip().lower()
        
        if status == 'running':
            ports = self.get_container_ports(container_name)
            web_url = self.get_container_web_url(container_name)
            
            basic_info.update({
                'ports': ports,
                'web_url': web_url,
                'has_web_interface': web_url is not None,
                'status': 'running'
            })
        else:
            basic_info['status'] = status
        
        return basic_info

    def get_container_network_info(self, container_name):
        """Get detailed network information for a container."""
        try:
            # Get container inspect data
            output = self._run_cmd([
                "podman", "inspect", container_name, "--format", "json"
            ])
            
            if output:
                container_info = json.loads(output)
                if isinstance(container_info, list) and container_info:
                    container_data = container_info[0]
                    
                    # Get network settings
                    network_settings = container_data.get('NetworkSettings', {})
                    
                    # Get ports
                    ports = self.get_container_ports(container_name)
                    
                    # Get networks
                    networks = network_settings.get('Networks', {})
                    network_list = []
                    
                    for network_name, network_info in networks.items():
                        ip_address = network_info.get('IPAddress', 'N/A')
                        gateway = network_info.get('Gateway', 'N/A')
                        network_list.append({
                            'name': network_name,
                            'ip_address': ip_address,
                            'gateway': gateway
                        })
                    
                    # Get hostname
                    hostname = container_data.get('Config', {}).get('Hostname', 'N/A')
                    
                    # Get DNS settings
                    dns = network_settings.get('DNSServers', [])
                    
                    return {
                        'ports': ports,
                        'networks': network_list,
                        'hostname': hostname,
                        'dns_servers': dns,
                        'ip_address': network_settings.get('IPAddress', 'N/A'),
                        'gateway': network_settings.get('Gateway', 'N/A'),
                        'mac_address': network_settings.get('MacAddress', 'N/A')
                    }
            
            return {
                'ports': [],
                'networks': [],
                'hostname': 'N/A',
                'dns_servers': [],
                'ip_address': 'N/A',
                'gateway': 'N/A',
                'mac_address': 'N/A'
            }
            
        except Exception as e:
            print(f"Error getting network info for {container_name}: {e}")
            return {
                'ports': [],
                'networks': [],
                'hostname': 'N/A',
                'dns_servers': [],
                'ip_address': 'N/A',
                'gateway': 'N/A',
                'mac_address': 'N/A',
                'error': str(e)
            }

    # ========== REGISTRY MANAGEMENT METHODS ==========

    def get_images(self):
        """Get list of all local images."""
        try:
            output = self._run_cmd(["podman", "images", "--format", "json"])
            if output:
                images = json.loads(output)
                return images if isinstance(images, list) else []
            return []
        except Exception as e:
            print(f"Error getting images: {e}")
            return []

    def search_images(self, query, limit=25):
        """Search for images in Docker Hub and other registries."""
        try:
            output = self._run_cmd([
                "podman", "search", query, "--limit", str(limit), "--format", "json"
            ])
            if output:
                results = json.loads(output)
                return results if isinstance(results, list) else []
            return []
        except Exception as e:
            print(f"Error searching images: {e}")
            return []

    def pull_image(self, image_name):
        """Pull an image from a registry."""
        try:
            self._run_cmd(["podman", "pull", image_name])
            print(f"✅ Image pulled successfully: {image_name}")
            return True
        except Exception as e:
            print(f"❌ Error pulling image {image_name}: {e}")
            return False

    def push_image(self, image_name, registry=None):
        """Push an image to a registry."""
        try:
            if registry:
                full_name = f"{registry}/{image_name}"
                self._run_cmd(["podman", "tag", image_name, full_name])
                self._run_cmd(["podman", "push", full_name])
            else:
                self._run_cmd(["podman", "push", image_name])
            print(f"✅ Image pushed successfully: {image_name}")
            return True
        except Exception as e:
            print(f"❌ Error pushing image {image_name}: {e}")
            return False

    def remove_image(self, image_name):
        """Remove a local image."""
        try:
            self._run_cmd(["podman", "rmi", image_name])
            print(f"✅ Image removed successfully: {image_name}")
            return True
        except Exception as e:
            print(f"❌ Error removing image {image_name}: {e}")
            return False

    def get_image_details(self, image_name):
        """Get detailed information about an image."""
        try:
            output = self._run_cmd([
                "podman", "inspect", image_name, "--format", "json"
            ])
            if output:
                image_info = json.loads(output)
                if isinstance(image_info, list) and image_info:
                    return image_info[0]
            return None
        except Exception as e:
            print(f"Error getting image details for {image_name}: {e}")
            return None

    def tag_image(self, source_image, target_image):
        """Tag an image with a new name."""
        try:
            self._run_cmd(["podman", "tag", source_image, target_image])
            print(f"✅ Image tagged successfully: {source_image} -> {target_image}")
            return True
        except Exception as e:
            print(f"❌ Error tagging image: {e}")
            return False

    def get_image_history(self, image_name):
        """Get the history/layers of an image."""
        try:
            output = self._run_cmd([
                "podman", "history", image_name, "--format", "json"
            ])
            if output:
                history = json.loads(output)
                return history if isinstance(history, list) else []
            return []
        except Exception as e:
            print(f"Error getting image history for {image_name}: {e}")
            return []

    def get_image_size(self, image_name):
        """Get the size of an image."""
        try:
            images = self.get_images()
            for image in images:
                if image_name in image.get('Names', []) or image_name == image.get('Repository', ''):
                    size = image.get('Size', 0)
                    return self._bytes_to_human(size) if isinstance(size, int) else size
            return 'N/A'
        except Exception as e:
            print(f"Error getting image size for {image_name}: {e}")
            return 'N/A'

    def get_all_images_info(self):
        """Get comprehensive information about all local images."""
        try:
            images = self.get_images()
            images_info = []
            
            for image in images:
                repo = image.get('Repository', 'unknown')
                tag = image.get('Tag', 'latest')
                image_id = image.get('Id', '')[:12]
                size = image.get('Size', 0)
                created = image.get('Created', 'unknown')
                
                # Convert size to human readable format
                if isinstance(size, int):
                    size_str = self._bytes_to_human(size)
                else:
                    size_str = str(size)
                
                images_info.append({
                    'repository': repo,
                    'tag': tag,
                    'image_id': image_id,
                    'size': size_str,
                    'created': created,
                    'full_name': f"{repo}:{tag}" if repo != 'unknown' else 'unknown'
                })
            
            return images_info
        except Exception as e:
            print(f"Error getting all images info: {e}")
            return []

    # In your podman_manager.py, add better error handling
    def get_containers(self):
        """Return a list of containers as JSON objects."""
        try:
            cmd = ["podman", "ps", "-a", "--format", "json"]
            print(f"🔍 Running Podman command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            print(f"🔍 Podman command completed. Return code: {result.returncode}")
            print(f"🔍 Podman stdout length: {len(result.stdout)}")
            print(f"🔍 Podman stderr: {result.stderr}")
            
            if not result.stdout.strip():
                print("⚠ No output from Podman command - no containers exist")
                return []
                
            containers = json.loads(result.stdout)
            print(f"✅ Podman returned {len(containers)} containers")
            print(f"✅ Containers type: {type(containers)}")
            
            # Debug: print container names and statuses
            for i, container in enumerate(containers):
                name = container.get("Names", ["unknown"])[0] if container.get("Names") else "unknown"
                status = container.get("Status", "unknown")
                state = container.get("State", "unknown")
                print(f"  📦 Container {i}: {name}")
                print(f"     Status: {status}")
                print(f"     State: {state}")
                print(f"     Image: {container.get('Image', 'unknown')}")
                
            return containers
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Podman command failed. Error: {e.stderr}")
            print(f"❌ Return code: {e.returncode}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse Podman JSON. Error: {e}")
            print(f"❌ Raw output: {result.stdout if 'result' in locals() else 'No output'}")
            return []
        except subprocess.TimeoutExpired:
            print("❌ Podman command timed out")
            return []
        except Exception as e:
            print(f"❌ Unexpected error in get_containers: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return []