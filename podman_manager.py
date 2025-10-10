import subprocess
import logging
import json

class PodmanManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def build_image(self, repo_path, image_name, tag="latest"):
        """Build a Podman image from a Dockerfile in the repo."""
        cmd = ["podman", "build", "-t", f"{image_name}:{tag}", repo_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(json.dumps({"event": "image_built", "image": f"{image_name}:{tag}"}))
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(json.dumps({"event": "build_error", "error": e.stderr}))
            return False

    def stop_container(self, container_name):
        """Stop and remove a running container."""
        try:
            subprocess.run(["podman", "stop", container_name], capture_output=True, text=True, check=True)
            subprocess.run(["podman", "rm", container_name], capture_output=True, text=True, check=True)
            self.logger.info(json.dumps({"event": "container_stopped", "container": container_name}))
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(json.dumps({"event": "stop_error", "error": e.stderr}))
            return False

    def run_container(self, image_name, container_name, tag="latest", ports=None):
        """Run a new container from the specified image."""
        cmd = ["podman", "run", "-d", "--name", container_name]
        if ports:
            cmd.extend(["-p", ports])
        cmd.append(f"{image_name}:{tag}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(json.dumps({"event": "container_started", "container": container_name}))
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(json.dumps({"event": "run_error", "error": e.stderr}))
            return False

    def get_container_status(self):
        """Get status of all containers."""
        try:
            result = subprocess.run(["podman", "ps", "-a", "--format", "json"], capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            self.logger.error(json.dumps({"event": "status_error", "error": e.stderr}))
            return []