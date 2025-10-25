from flask import request
import json
import os
import logging
import subprocess
import tempfile
import datetime
import shutil

logger = logging.getLogger('autopod')

def handle_webhook(podman_manager):
    """Process GitHub webhook payload and trigger Podman actions."""
    payload = request.get_json()
    
    logger.info(f"📨 Received webhook payload")
    
    # Handle different webhook payload formats
    repo_url = None
    repo_name = "webhook-app"  # Default name
    
    if payload and 'repository' in payload:
        # Standard GitHub webhook format
        repo_url = payload['repository'].get('clone_url')
        repo_name = payload['repository'].get('name', 'webhook-app')
        logger.info(f"🔧 Processing GitHub repository: {repo_name}")
    elif payload and 'test' in payload:
        # Test payload format
        repo_name = "test-app"
        logger.info(f"🧪 Processing test webhook: {repo_name}")
    else:
        logger.error("❌ Invalid webhook payload format")
        return {"status": "error", "message": "Invalid webhook payload: missing 'repository' or 'test' field"}, 400

    # Extract repository name from URL if provided
    if repo_url:
        extracted_name = extract_repo_name_from_url(repo_url)
        if extracted_name and extracted_name != "webhook-app":
            repo_name = extracted_name
            logger.info(f"🔍 Extracted repository name from URL: {repo_name}")

    # Create a temporary directory for the repository
    temp_dir = tempfile.mkdtemp(prefix="autopod_")
    repo_path = os.path.join(temp_dir, repo_name)
    
    logger.info(f"📁 Working directory: {repo_path}")

    try:
        # Try to clone the repository if it's a real GitHub URL
        if repo_url and repo_url.startswith("https://github.com/"):
            logger.info(f"🔗 Attempting to clone repository: {repo_url}")
            clone_success = clone_repository(repo_url, repo_path)
            
            if not clone_success:
                logger.warning("📝 Git clone failed, creating demo project instead")
                create_demo_project(repo_path, repo_name)
            else:
                logger.info("✅ Repository cloned successfully")
                
                # Check if Dockerfile exists in cloned repository
                if not os.path.exists(os.path.join(repo_path, "Dockerfile")):
                    logger.warning("📦 No Dockerfile found in repository, creating demo project")
                    create_demo_project(repo_path, repo_name)
        else:
            # Create demo project for non-GitHub URLs or test deployments
            logger.info(f"📝 Creating demo project for: {repo_name}")
            create_demo_project(repo_path, repo_name)

        # Podman container lifecycle management
        image_name = f"autopod-{repo_name.lower().replace(' ', '-')}"
        container_name = f"{image_name}-container"
        
        logger.info(f"🚀 Starting container lifecycle: {image_name} -> {container_name}")

        # Step 1: Build image using Podman
        logger.info(f"🔨 Building image: {image_name}")
        build_success = podman_manager.build_image(repo_path, image_name)
        
        if not build_success:
            logger.error(f"❌ Image build failed: {image_name}")
            return {"status": "error", "message": f"Image build failed for {image_name}"}, 500

        logger.info(f"✅ Image built successfully: {image_name}")

        # Step 2: Stop and remove existing container if running
        logger.info(f"🛑 Stopping existing container: {container_name}")
        podman_manager.stop_container(container_name)  # This will fail silently if container doesn't exist
        podman_manager.remove_container(container_name)  # This will fail silently if container doesn't exist

        # Step 3: Run new container with Podman
        logger.info(f"▶️ Running new container: {container_name}")
        
        # Find an available port
        port = find_available_port(8081)
        logger.info(f"🔌 Using port: {port}")
        
        run_success = podman_manager.run_container(image_name, container_name, ports=f"{port}:80")
        
        if not run_success:
            logger.error(f"❌ Container run failed: {container_name}")
            return {"status": "error", "message": f"Failed to run container {container_name}"}, 500

        logger.info(f"✅ Container started successfully: {container_name} on port {port}")

        # Step 4: Sync with database to update frontend
        logger.info("💾 Syncing with database...")
        podman_manager.sync_with_db()
        
        logger.info(f"🎉 Successfully deployed {container_name}")

        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info("🧹 Temporary files cleaned up")
        
        return {
            "status": "success", 
            "message": f"Container {container_name} deployed successfully on port {port}",
            "container_name": container_name,
            "image_name": image_name,
            "port": port,
            "access_url": f"http://127.0.0.1:{port}",
            "repo_name": repo_name
        }

    except Exception as e:
        logger.exception(f"💥 Error in webhook processing: {e}")
        # Clean up temporary directory on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"status": "error", "message": f"Webhook processing failed: {str(e)}"}, 500

def extract_repo_name_from_url(repo_url):
    """Extract repository name from GitHub URL."""
    try:
        if not repo_url:
            return "webhook-app"
            
        # Remove .git suffix and trailing slashes
        clean_url = repo_url.rstrip('/').replace('.git', '')
        
        # Extract repository name from different GitHub URL formats
        if 'github.com' in clean_url:
            parts = clean_url.split('/')
            # Find the part after github.com/username/
            if len(parts) >= 5:  # https://github.com/username/repo
                repo_name = parts[4]
            elif len(parts) >= 2:  # github.com/username/repo
                repo_name = parts[-1]
            else:
                repo_name = "webhook-app"
            
            # Validate repository name
            if repo_name and repo_name != "webhook-app":
                # Clean up the name
                repo_name = repo_name.lower().replace(' ', '-')
                return repo_name
                
    except Exception as e:
        logger.warning(f"⚠️ Could not extract repo name from URL: {e}")
    
    return "webhook-app"

def clone_repository(repo_url, repo_path):
    """Clone a Git repository with timeout and error handling."""
    try:
        cmd = ["git", "clone", "--depth", "1", repo_url, repo_path]
        logger.info(f"🔗 Cloning: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=120,  # 2 minute timeout
            check=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Git clone successful")
            return True
        else:
            logger.error(f"❌ Git clone failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("⏰ Git clone timeout - repository too large or network issue")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Git clone process error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during git clone: {e}")
        return False

def create_demo_project(repo_path, repo_name):
    """Create a demo project structure with a Dockerfile."""
    os.makedirs(repo_path, exist_ok=True)
    
    # Get current timestamp for the demo page
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create a simple Dockerfile
    dockerfile_content = """FROM nginx:alpine

# Copy custom HTML file
COPY index.html /usr/share/nginx/html/index.html

# Create build info file
RUN echo "AutoPod Demo Build" > /usr/share/nginx/html/build-info.txt

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
"""
    
    # Create a custom HTML file
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>AutoPod Demo - {repo_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            max-width: 800px;
            margin: 20px;
            padding: 40px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            text-align: center;
        }}
        h1 {{
            font-size: 3em;
            margin-bottom: 20px;
            color: #66fcf1;
        }}
        h2 {{
            font-size: 1.5em;
            margin-bottom: 30px;
            opacity: 0.9;
        }}
        .status {{
            background: rgba(46, 204, 113, 0.2);
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            border: 1px solid #2ecc71;
        }}
        .info {{
            background: rgba(52, 152, 219, 0.2);
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            border: 1px solid #3498db;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 AutoPod</h1>
        <h2>Intelligent Container Deployment</h2>
        
        <div class="status">
            <h3>✅ Deployment Successful!</h3>
            <p>Repository: <strong>{repo_name}</strong></p>
        </div>
        
        <div class="info">
            <p>🕒 Deployed at: {current_time}</p>
            <p>🐳 Powered by Podman</p>
            <p>🤖 Automated by AutoPod</p>
        </div>
        
        <p>This container was automatically built and deployed via webhook trigger!</p>
    </div>
</body>
</html>
"""
    
    # Write Dockerfile with proper encoding
    with open(os.path.join(repo_path, "Dockerfile"), "w", encoding='utf-8') as f:
        f.write(dockerfile_content)
    
    # Write HTML file with proper encoding
    with open(os.path.join(repo_path, "index.html"), "w", encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"📄 Demo project created at: {repo_path}")

def find_available_port(start_port=8081):
    """Find an available port starting from start_port."""
    import socket
    port = start_port
    max_port = start_port + 50  # Search up to 50 ports
    
    while port <= max_port:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            port += 1
    
    # If no port found, return the original (might fail, but we try)
    logger.warning(f"⚠️  No available ports found, using {start_port}")
    return start_port