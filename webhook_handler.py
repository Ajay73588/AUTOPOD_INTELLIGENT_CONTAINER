from flask import request
import json
import os
import logging
import subprocess

logger = logging.getLogger('autopod')

def handle_webhook(podman_manager):
    """Process GitHub webhook payload and trigger Podman actions."""
    payload = request.get_json()
    
    if not payload or 'repository' not in payload:
        logger.error("Invalid webhook payload")
        raise ValueError("Invalid webhook payload")

    repo_url = payload['repository']['clone_url']
    repo_name = payload['repository']['name']
    commit_id = payload.get('after', 'unknown')
    
    # Clone or pull the repository
    repo_path = f"/tmp/{repo_name}"
    if os.path.exists(repo_path):
        cmd = ["git", "-C", repo_path, "pull"]
    else:
        cmd = ["git", "clone", repo_url, repo_path]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Repository updated: {repo_name}, commit: {commit_id}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git error: {e.stderr}")
        raise

    # Podman container lifecycle management
    image_name = repo_name.lower()
    container_name = f"{image_name}-container"
    
    # Build image using Podman
    if podman_manager.build_image(repo_path, image_name):
        # Stop and remove existing container if running
        podman_manager.stop_container(container_name)
        podman_manager.remove_container(container_name)
        
        # Run new container with Podman
        podman_manager.run_container(image_name, container_name, ports="8080:8080")
        
        # Sync with database to update frontend
        podman_manager.sync_with_db()
        
        logger.info(f"Successfully deployed {container_name}")
    else:
        logger.error(f"Failed to build image for {repo_name}")
        raise RuntimeError(f"Image build failed for {repo_name}")