from flask import request
import json
import os
import logging

def handle_webhook(podman_manager):
    """Process GitHub webhook payload and trigger Podman actions."""
    logger = logging.getLogger(__name__)
    payload = request.get_json()
    
    if not payload or 'repository' not in payload:
        raise ValueError("Invalid webhook payload")

    repo_url = payload['repository']['clone_url']
    repo_name = payload['repository']['name']
    commit_id = payload['after']
    
    # Clone or pull the repository
    repo_path = f"/tmp/{repo_name}"
    if os.path.exists(repo_path):
        cmd = ["git", "-C", repo_path, "pull"]
    else:
        cmd = ["git", "clone", repo_url, repo_path]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(json.dumps({"event": "repo_updated", "repo": repo_name, "commit": commit_id}))
    except subprocess.CalledProcessError as e:
        logger.error(json.dumps({"event": "git_error", "error": e.stderr}))
        raise

    # Automate Podman lifecycle
    image_name = repo_name.lower()
    container_name = f"{image_name}-container"
    
    podman_manager.build_image(repo_path, image_name)
    podman_manager.stop_container(container_name)
    podman_manager.run_container(image_name, container_name, ports="8080:8080")