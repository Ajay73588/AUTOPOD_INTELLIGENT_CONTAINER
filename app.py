import os
import logging
from logging.handlers import RotatingFileHandler
import json
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS  # Add this import
from webhook_handler import handle_webhook
from podman_manager import PodmanManager
from database import init_db, get_container_logs, get_container_status
import atexit
from database import close_db_connection
import subprocess

app = Flask(__name__)

# Enhanced CORS configuration for React frontend
CORS(app, 
     origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://frontend:80","http://frontend:3000"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin"],
     supports_credentials=True)

# Ensure logs folder exists
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'autopod.log')

# Configure rotating file logging
logger = logging.getLogger('autopod')
logger.setLevel(logging.INFO)

# Avoid adding multiple handlers if module reloaded
if not logger.handlers:
    handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

# Also route Flask's logger to the same handlers
app.logger.handlers = logger.handlers
app.logger.setLevel(logger.level)

# Initialize Podman manager and database (safe init with logging)
try:
    podman = PodmanManager()
    logger.info("PodmanManager initialized successfully")
except Exception as e:
    logger.exception("Failed to initialize PodmanManager")
    podman = None

try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.exception("Failed to initialize database")

# Clean up database connections on app exit
@atexit.register
def cleanup():
    close_db_connection()
    logger.info("Database connections cleaned up")

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to allow frontend requests."""
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Access-Control-Allow-Origin'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@app.route('/')
def dashboard():
    """Render the main dashboard page."""
    return jsonify({
        "message": "AutoPod API is running! Use React frontend at http://localhost:3000",
        "status": "active",
        "version": "1.0.0"
    })

@app.route('/api/status')
def api_status():
    """API endpoint to get container statuses."""
    try:
        statuses = get_container_status()
        logger.info(f"Fetched {len(statuses)} container statuses")
        return jsonify({"success": True, "data": statuses})
    except Exception as e:
        logger.exception("Error fetching container statuses")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logs')
def api_logs():
    """API endpoint to get container logs."""
    try:
        logs = get_container_logs()
        logger.info(f"Fetched {len(logs)} log entries")
        return jsonify({"success": True, "data": logs})
    except Exception as e:
        logger.exception("Error fetching logs")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/sync', methods=['POST', 'OPTIONS'])
def api_sync():
    """API endpoint to manually sync Podman containers with database."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        podman.sync_with_db()
        logger.info("Manual sync completed successfully")
        return jsonify({"success": True, "message": "Sync completed successfully"})
    except Exception as e:
        logger.exception("Error syncing containers")
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/api/containers', methods=['GET'])
def api_containers():
    """API endpoint to get raw Podman container data."""
    try:
        if podman is None:
            print("❌ PodmanManager not initialized")
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        print("🔍 Getting containers from Podman...")
        containers = podman.get_containers()
        print(f"📊 Raw containers from Podman: {containers}")
        print(f"📦 Number of containers found: {len(containers)}")
        
        # If containers is None, set to empty list
        if containers is None:
            containers = []
            print("⚠️ Containers was None, setting to empty list")
        
        # Log each container for debugging
        for i, container in enumerate(containers):
            container_name = container.get("Names", ["No Name"])[0] if container.get("Names") else "No Name"
            container_state = container.get("State", "No State")
            print(f"  Container {i}: {container_name} - {container_state}")
        
        logger.info(f"Fetched {len(containers)} raw containers from Podman")
        
        return jsonify({
            "success": True, 
            "data": containers,
            "count": len(containers),
            "message": f"Found {len(containers)} containers",
            "debug": {
                "podman_initialized": podman is not None,
                "containers_type": type(containers).__name__,
                "containers_length": len(containers)
            }
        })
    except Exception as e:
        print(f"💥 Error in api_containers: {str(e)}")
        import traceback
        print(f"💥 Traceback: {traceback.format_exc()}")
        logger.exception("Error fetching raw container data")
        return jsonify({"success": False, "error": str(e)}), 500
    
        
@app.route('/api/debug/containers', methods=['GET'])
def api_debug_containers():
    """Debug endpoint to see raw Podman container data."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        containers = podman.get_containers()
        return jsonify({
            "success": True, 
            "container_count": len(containers),
            "data": containers
        })
    except Exception as e:
        logger.exception("Error in debug endpoint")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/webhook', methods=['POST', 'OPTIONS'])
def webhook():
    """Handle GitHub webhook events."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        print("🔍 Webhook received - starting deployment")
        print(f"🔍 Headers: {dict(request.headers)}")
        
        if podman is None:
            print("❌ PodmanManager not initialized")
            return jsonify({"status": "error", "message": "PodmanManager not initialized"}), 500
        
        # Get JSON data from request
        data = request.get_json()
        print(f"🔍 Webhook data: {data}")
        
        if data is None:
            print("❌ No JSON data received")
            return jsonify({"status": "error", "message": "No JSON data received"}), 400
        
        # Process webhook immediately (for now)
        print("🔄 Processing webhook...")
        result = handle_webhook(podman, data)
        print(f"✅ Webhook processing completed: {result}")
        
        return jsonify({
            "status": "success", 
            "message": "Deployment completed successfully",
            "data": result
        }), 200
        
    except Exception as e:
        logger.exception("Webhook handling error")
        print(f"💥 Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "podman_initialized": podman is not None,
        "database_initialized": True,
        "frontend_ready": True
    })

# Docker Hub Authentication Endpoints - ADDED
@app.route('/api/docker/login', methods=['POST', 'OPTIONS'])
def docker_login():
    """Login to Docker Hub using provided credentials."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        registry = data.get('registry', 'docker.io')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password are required'
            }), 400
        
        # Store credentials in environment variables
        os.environ['DOCKER_USERNAME'] = username
        os.environ['DOCKER_PASSWORD'] = password
        os.environ['DOCKER_REGISTRY'] = registry
        
        # Test the login
        result = subprocess.run([
            'podman', 'login', '-u', username, '-p', password, registry
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Successfully logged in to Docker Hub as {username}")
            return jsonify({
                'success': True,
                'message': 'Successfully logged in to Docker Hub'
            })
        else:
            # Clear credentials if login fails
            os.environ.pop('DOCKER_USERNAME', None)
            os.environ.pop('DOCKER_PASSWORD', None)
            os.environ.pop('DOCKER_REGISTRY', None)
            logger.error(f"Docker Hub login failed: {result.stderr}")
            return jsonify({
                'success': False,
                'error': f'Login failed: {result.stderr}'
            }), 400
            
    except Exception as e:
        logger.exception("Error during Docker Hub login")
        return jsonify({
            'success': False,
            'error': f'Login error: {str(e)}'
        }), 500

@app.route('/api/docker/logout', methods=['POST', 'OPTIONS'])
def docker_logout():
    """Logout from Docker Hub and clear credentials."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Clear environment variables
        os.environ.pop('DOCKER_USERNAME', None)
        os.environ.pop('DOCKER_PASSWORD', None)
        os.environ.pop('DOCKER_REGISTRY', None)
        
        # Logout from Podman
        result = subprocess.run(['podman', 'logout', 'docker.io'], 
                              capture_output=True, text=True)
        
        logger.info("Successfully logged out from Docker Hub")
        return jsonify({
            'success': True,
            'message': 'Successfully logged out from Docker Hub'
        })
        
    except Exception as e:
        logger.exception("Error during Docker Hub logout")
        return jsonify({
            'success': False,
            'error': f'Logout error: {str(e)}'
        }), 500

@app.route('/api/docker/check-login', methods=['GET'])
def check_docker_login():
    """Check if currently logged in to Docker Hub."""
    try:
        username = os.environ.get('DOCKER_USERNAME')
        
        if username:
            # Verify login is still valid
            result = subprocess.run(['podman', 'search', f'{username}/test'], 
                                  capture_output=True, text=True)
            
            logged_in = result.returncode == 0
            
            logger.info(f"Docker Hub login check: logged_in={logged_in}, username={username}")
            return jsonify({
                'success': True,
                'logged_in': logged_in,
                'username': username
            })
        else:
            logger.info("Docker Hub login check: not logged in")
            return jsonify({
                'success': True,
                'logged_in': False,
                'username': None
            })
            
    except Exception as e:
        logger.exception("Error checking Docker Hub login status")
        return jsonify({
            'success': False,
            'error': f'Error checking login status: {str(e)}'
        }), 500

@app.route('/api/docker/push', methods=['POST', 'OPTIONS'])
def docker_push_image():
    """Push container image to Docker Hub."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        image_name = data.get('image_name')
        username = data.get('username')
        registry = data.get('registry', 'docker.io')
        
        if not image_name or not username:
            return jsonify({
                'success': False,
                'error': 'Image name and username are required'
            }), 400
        
        # Tag the image
        tagged_name = f'{registry}/{username}/{image_name}:latest'
        
        # Tag the image
        tag_result = subprocess.run([
            'podman', 'tag', image_name, tagged_name
        ], capture_output=True, text=True)
        
        if tag_result.returncode != 0:
            logger.error(f"Failed to tag image {image_name}: {tag_result.stderr}")
            return jsonify({
                'success': False,
                'error': f'Failed to tag image: {tag_result.stderr}'
            }), 400
        
        # Push the image
        push_result = subprocess.run([
            'podman', 'push', tagged_name
        ], capture_output=True, text=True)
        
        if push_result.returncode == 0:
            logger.info(f"Successfully pushed image {tagged_name} to Docker Hub")
            return jsonify({
                'success': True,
                'data': {
                    'tagged_name': tagged_name,
                    'registry_url': f'https://hub.docker.com/r/{username}/{image_name}',
                    'pull_command': f'podman pull {tagged_name}'
                }
            })
        else:
            logger.error(f"Failed to push image {tagged_name}: {push_result.stderr}")
            return jsonify({
                'success': False,
                'error': f'Push failed: {push_result.stderr}'
            }), 400
            
    except Exception as e:
        logger.exception("Error pushing image to Docker Hub")
        return jsonify({
            'success': False,
            'error': f'Push error: {str(e)}'
        }), 500

# Container Management Endpoints
@app.route('/api/containers/start', methods=['POST', 'OPTIONS'])
def api_start_container():
    """API endpoint to start a container."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        container_name = data.get('container_name')
        
        if not container_name:
            return jsonify({"success": False, "error": "Container name is required"}), 400
        
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        success = podman.start_container(container_name)
        if success:
            podman.sync_with_db()  # Update the database
            logger.info(f"Container {container_name} started successfully")
            return jsonify({"success": True, "message": f"Container {container_name} started"})
        else:
            logger.error(f"Failed to start container {container_name}")
            return jsonify({"success": False, "error": f"Failed to start container {container_name}"}), 500
            
    except Exception as e:
        logger.exception("Error starting container")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/containers/stop', methods=['POST', 'OPTIONS'])
def api_stop_container():
    """API endpoint to stop a container."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        container_name = data.get('container_name')
        
        if not container_name:
            return jsonify({"success": False, "error": "Container name is required"}), 400
        
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        success = podman.stop_container(container_name)
        if success:
            podman.sync_with_db()  # Update the database
            logger.info(f"Container {container_name} stopped successfully")
            return jsonify({"success": True, "message": f"Container {container_name} stopped"})
        else:
            logger.error(f"Failed to stop container {container_name}")
            return jsonify({"success": False, "error": f"Failed to stop container {container_name}"}), 500
            
    except Exception as e:
        logger.exception("Error stopping container")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/containers/restart', methods=['POST', 'OPTIONS'])
def api_restart_container():
    """API endpoint to restart a container."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        container_name = data.get('container_name')
        
        if not container_name:
            return jsonify({"success": False, "error": "Container name is required"}), 400
        
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        success = podman.restart_container(container_name)
        if success:
            podman.sync_with_db()  # Update the database
            logger.info(f"Container {container_name} restarted successfully")
            return jsonify({"success": True, "message": f"Container {container_name} restarted"})
        else:
            logger.error(f"Failed to restart container {container_name}")
            return jsonify({"success": False, "error": f"Failed to restart container {container_name}"}), 500
            
    except Exception as e:
        logger.exception("Error restarting container")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/containers/remove', methods=['POST', 'OPTIONS'])
def api_remove_container():
    """API endpoint to remove a container."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        container_name = data.get('container_name')
        
        if not container_name:
            return jsonify({"success": False, "error": "Container name is required"}), 400
        
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        success = podman.remove_container(container_name)
        if success:
            podman.sync_with_db()  # Update the database
            logger.info(f"Container {container_name} removed successfully")
            return jsonify({"success": True, "message": f"Container {container_name} removed"})
        else:
            logger.error(f"Failed to remove container {container_name}")
            return jsonify({"success": False, "error": f"Failed to remove container {container_name}"}), 500
            
    except Exception as e:
        logger.exception("Error removing container")
        return jsonify({"success": False, "error": str(e)}), 500

# Health Monitoring Endpoints
@app.route('/api/containers/<container_name>/health', methods=['GET'])
def api_container_health(container_name):
    """Get detailed health information for a container."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        health_data = {
            'health': podman.get_container_health(container_name),
            'resources': podman.get_container_resources(container_name)
        }
        
        return jsonify({"success": True, "data": health_data})
    except Exception as e:
        logger.exception(f"Error getting health for {container_name}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/containers/health', methods=['GET'])
def api_all_containers_health():
    """Get health status for all containers."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        health_data = podman.get_all_containers_health()
        return jsonify({"success": True, "data": health_data})
    except Exception as e:
        logger.exception("Error getting all containers health")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/containers/<container_name>/stats', methods=['GET'])
def api_container_stats(container_name):
    """Get real-time statistics for a container."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        stats_data = podman.get_container_stats(container_name)
        return jsonify({"success": True, "data": stats_data})
    except Exception as e:
        logger.exception(f"Error getting stats for {container_name}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/api/containers/<container_name>/weburl', methods=['GET'])
def api_container_weburl(container_name):
    """Get the web URL for a container."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        web_url = podman.get_container_web_url(container_name)
        container_status = podman.get_container_status_for_ui(container_name)
        
        return jsonify({
            "success": True, 
            "data": {
                "web_url": web_url,
                "has_web_interface": container_status['has_web_interface'],
                "ports": container_status['ports'],
                "status": container_status['status']
            }
        })
    except Exception as e:
        logger.exception(f"Error getting web URL for {container_name}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/containers/<container_name>/open', methods=['POST', 'OPTIONS'])
def api_open_container_web(container_name):
    """Open container's web interface."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        web_url = podman.get_container_web_url(container_name)
        
        if not web_url:
            return jsonify({
                "success": False, 
                "error": "No web interface found or container not running"
            }), 404
        
        # Return the URL for the frontend to open
        return jsonify({
            "success": True, 
            "data": {
                "web_url": web_url,
                "message": f"Web interface available at: {web_url}"
            }
        })
    except Exception as e:
        logger.exception(f"Error opening web interface for {container_name}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/containers/<container_name>/network', methods=['GET'])
def api_container_network(container_name):
    """Get detailed network information for a container."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        network_data = podman.get_container_network_info(container_name)
        return jsonify({"success": True, "data": network_data})
    except Exception as e:
        logger.exception(f"Error getting network info for {container_name}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/containers/network/all', methods=['GET'])
def api_all_containers_network():
    """Get network information for all containers."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        containers = podman.get_containers()
        network_data = {}
        
        for container in containers:
            container_name = container.get('Names', ['unknown'])[0]
            try:
                network_data[container_name] = podman.get_container_network_info(container_name)
            except Exception as e:
                logger.warning(f"Could not get network info for {container_name}: {e}")
                network_data[container_name] = {
                    'ports': [],
                    'networks': [],
                    'ip_address': 'N/A',
                    'gateway': 'N/A',
                    'error': str(e)
                }
        
        logger.info(f"Fetched network info for {len(network_data)} containers")
        return jsonify({"success": True, "data": network_data})
    except Exception as e:
        logger.exception("Error getting all containers network info")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/network/stats', methods=['GET'])
def api_network_stats():
    """Get network statistics and summary."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        containers = podman.get_containers()
        total_containers = len(containers)
        containers_with_ports = 0
        total_ports = 0
        networks_list = set()
        
        for container in containers:
            container_name = container.get('Names', ['unknown'])[0]
            try:
                network_info = podman.get_container_network_info(container_name)
                if network_info.get('ports'):
                    containers_with_ports += 1
                    total_ports += len(network_info['ports'])
                if network_info.get('networks'):
                    networks_list.update(network_info['networks'])
            except:
                pass
        
        stats = {
            'total_containers': total_containers,
            'containers_with_ports': containers_with_ports,
            'total_ports_exposed': total_ports,
            'unique_networks': len(networks_list),
            'networks': list(networks_list)
        }
        
        logger.info("Fetched network statistics")
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        logger.exception("Error getting network stats")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logs/advanced', methods=['GET'])
def api_logs_advanced():
    """Advanced logging endpoint with filtering, searching, and pagination."""
    try:
        # Get query parameters
        container_name = request.args.get('container', None)
        search_query = request.args.get('search', None)
        log_type = request.args.get('type', None)  # 'info', 'error', 'warning'
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        logs = get_container_logs()
        
        # Filter by container name
        if container_name:
            logs = [log for log in logs if log.get('container_name') == container_name]
        
        # Filter by log type
        if log_type:
            logs = [log for log in logs if log_type.lower() in log.get('log', '').lower()]
        
        # Search in logs
        if search_query:
            logs = [log for log in logs if search_query.lower() in log.get('log', '').lower()]
        
        # Pagination
        total = len(logs)
        logs = logs[offset:offset + limit]
        
        logger.info(f"Advanced logs fetched: {len(logs)} entries from {total} total")
        return jsonify({
            "success": True,
            "data": logs,
            "total": total,
            "limit": limit,
            "offset": offset
        })
    except Exception as e:
        logger.exception("Error fetching advanced logs")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logs/export', methods=['GET'])
def api_logs_export():
    """Export logs in JSON or CSV format."""
    try:
        format_type = request.args.get('format', 'json')  # 'json' or 'csv'
        container_name = request.args.get('container', None)
        
        logs = get_container_logs()
        
        if container_name:
            logs = [log for log in logs if log.get('container_name') == container_name]
        
        if format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=['timestamp', 'container_name', 'log'])
            writer.writeheader()
            writer.writerows(logs)
            
            logger.info(f"Exported {len(logs)} logs as CSV")
            return output.getvalue(), 200, {
                'Content-Disposition': 'attachment; filename=logs.csv',
                'Content-Type': 'text/csv'
            }
        else:
            logger.info(f"Exported {len(logs)} logs as JSON")
            return jsonify({
                "success": True,
                "data": logs,
                "count": len(logs)
            })
    except Exception as e:
        logger.exception("Error exporting logs")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logs/stream', methods=['GET'])
def api_logs_stream():
    """Stream logs in real-time (Server-Sent Events)."""
    try:
        def generate():
            last_count = 0
            while True:
                logs = get_container_logs()
                if len(logs) > last_count:
                    new_logs = logs[last_count:]
                    for log in new_logs:
                        yield f"data: {json.dumps(log)}\n\n"
                    last_count = len(logs)
                import time
                time.sleep(1)
        
        return generate(), 200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    except Exception as e:
        logger.exception("Error streaming logs")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/images', methods=['GET'])
def api_get_images():
    """Get list of all local images."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        images = podman.get_all_images_info()
        logger.info(f"Fetched {len(images)} local images")
        return jsonify({"success": True, "data": images})
    except Exception as e:
        logger.exception("Error fetching images")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/images/search', methods=['GET'])
def api_search_images():
    """Search for images in registries."""
    try:
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 25))
        
        if not query:
            return jsonify({"success": False, "error": "Search query is required"}), 400
        
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        results = podman.search_images(query, limit)
        logger.info(f"Searched for images: {query} - Found {len(results)} results")
        return jsonify({"success": True, "data": results})
    except Exception as e:
        logger.exception("Error searching images")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/images/pull', methods=['POST', 'OPTIONS'])
def api_pull_image():
    """Pull an image from a registry."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        image_name = data.get('image_name')
        
        if not image_name:
            return jsonify({"success": False, "error": "Image name is required"}), 400
        
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        success = podman.pull_image(image_name)
        if success:
            logger.info(f"Image pulled successfully: {image_name}")
            return jsonify({"success": True, "message": f"Image {image_name} pulled successfully"})
        else:
            return jsonify({"success": False, "error": f"Failed to pull image {image_name}"}), 500
    except Exception as e:
        logger.exception("Error pulling image")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/images/push', methods=['POST', 'OPTIONS'])
def api_push_image():
    """Push an image to a registry."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        image_name = data.get('image_name')
        registry = data.get('registry', None)
        
        if not image_name:
            return jsonify({"success": False, "error": "Image name is required"}), 400
        
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        success = podman.push_image(image_name, registry)
        if success:
            logger.info(f"Image pushed successfully: {image_name}")
            return jsonify({"success": True, "message": f"Image {image_name} pushed successfully"})
        else:
            return jsonify({"success": False, "error": f"Failed to push image {image_name}"}), 500
    except Exception as e:
        logger.exception("Error pushing image")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/images/remove', methods=['POST', 'OPTIONS'])
def api_remove_image():
    """Remove a local image."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        image_name = data.get('image_name')
        
        if not image_name:
            return jsonify({"success": False, "error": "Image name is required"}), 400
        
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        success = podman.remove_image(image_name)
        if success:
            logger.info(f"Image removed successfully: {image_name}")
            return jsonify({"success": True, "message": f"Image {image_name} removed successfully"})
        else:
            return jsonify({"success": False, "error": f"Failed to remove image {image_name}"}), 500
    except Exception as e:
        logger.exception("Error removing image")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/images/<image_name>/details', methods=['GET'])
def api_image_details(image_name):
    """Get detailed information about an image."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        details = podman.get_image_details(image_name)
        if details:
            logger.info(f"Fetched details for image: {image_name}")
            return jsonify({"success": True, "data": details})
        else:
            return jsonify({"success": False, "error": f"Image {image_name} not found"}), 404
    except Exception as e:
        logger.exception(f"Error getting image details for {image_name}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/images/<image_name>/history', methods=['GET'])
def api_image_history(image_name):
    """Get the history/layers of an image."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        history = podman.get_image_history(image_name)
        logger.info(f"Fetched history for image: {image_name}")
        return jsonify({"success": True, "data": history})
    except Exception as e:
        logger.exception(f"Error getting image history for {image_name}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/images/tag', methods=['POST', 'OPTIONS'])
def api_tag_image():
    """Tag an image with a new name."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        source_image = data.get('source_image')
        target_image = data.get('target_image')
        
        if not source_image or not target_image:
            return jsonify({"success": False, "error": "Source and target image names are required"}), 400
        
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        success = podman.tag_image(source_image, target_image)
        if success:
            logger.info(f"Image tagged: {source_image} -> {target_image}")
            return jsonify({"success": True, "message": f"Image tagged successfully"})
        else:
            return jsonify({"success": False, "error": "Failed to tag image"}), 500
    except Exception as e:
        logger.exception("Error tagging image")
        return jsonify({"success": False, "error": str(e)}), 500

# Add missing method implementations to handle undefined methods
@app.route('/api/containers/<container_name>/resources', methods=['GET'])
def api_container_resources(container_name):
    """Get container resource usage and limits."""
    try:
        if podman is None:
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        # Create a simple resources response if method doesn't exist
        try:
            resources = podman.get_container_resources(container_name)
        except AttributeError:
            # Fallback if method doesn't exist
            resources = {
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
        
        return jsonify({"success": True, "data": resources})
    except Exception as e:
        logger.exception(f"Error getting resources for {container_name}")
        return jsonify({"success": False, "error": str(e)}), 500

# Add fallback for get_container_status_for_ui if it doesn't exist
def get_container_status_for_ui_fallback(container_name):
    """Fallback method for container status UI."""
    return {
        'name': container_name,
        'web_url': None,
        'has_web_interface': False,
        'ports': [],
        'status': 'unknown'
    }

# Add fallback for get_container_web_url if it doesn't exist  
def get_container_web_url_fallback(container_name):
    """Fallback method for container web URL."""
    return None


@app.route('/api/debug/podman-health')
def debug_podman_health():
    """Debug endpoint to check Podman connectivity."""
    try:
        podman = PodmanManager()
        health = podman.health_check()
        containers = podman.get_containers()
        
        return jsonify({
            'podman_health': health,
            'container_count': len(containers),
            'socket_path': os.getenv('PODMAN_SOCKET', '/run/podman/podman.sock'),
            'socket_exists': os.path.exists(os.getenv('PODMAN_SOCKET', '/run/podman/podman.sock')),
            'in_docker': os.path.exists('/.dockerenv'),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Monkey patch missing methods if they don't exist
if podman is not None:
    if not hasattr(podman, 'get_container_resources'):
        podman.get_container_resources = lambda name: {
            'cpu_percent': '0%',
            'memory_usage': '0B', 
            'memory_limit': 'N/A',
            'network_io': '0B / 0B',
            'block_io': '0B / 0B',
            'pids': '0',
            'restart_count': 0,
            'created_at': 'unknown',
            'container_name': name
        }
    
    if not hasattr(podman, 'get_container_status_for_ui'):
        podman.get_container_status_for_ui = get_container_status_for_ui_fallback
        
    if not hasattr(podman, 'get_container_web_url'):
        podman.get_container_web_url = get_container_web_url_fallback
        
    if not hasattr(podman, 'get_all_containers_health'):
        podman.get_all_containers_health = lambda: {}
        
    if not hasattr(podman, 'get_container_network_info'):
        podman.get_container_network_info = lambda name: {
            'ports': [],
            'networks': [],
            'hostname': 'N/A',
            'dns_servers': [],
            'ip_address': 'N/A',
            'gateway': 'N/A',
            'mac_address': 'N/A'
        }

if __name__ == '__main__':
    # Install flask-cors if not already installed
    try:
        import flask_cors
    except ImportError:
        print("⚠️  Installing flask-cors...")
        import subprocess
        subprocess.check_call(["pip", "install", "flask-cors"])
        print("✅ flask-cors installed successfully!")
    
    # Perform initial sync when starting the application
    if podman:
        try:
            logger.info("Performing initial sync on startup...")
            podman.sync_with_db()
            logger.info("Initial sync completed on startup")
        except Exception as e:
            logger.error(f"Initial sync failed: {e}")
    
    # ADD THESE EXPLICIT PRINT STATEMENTS
    print("\n" + "="*60)
    print("🚀 AUTOPOD Flask Application Starting!")
    print("="*60)
    print("📡 Server URLs:")
    print(f"   • http://127.0.0.1:5000")
    print(f"   • http://localhost:5000") 
    print(f"   • http://10.3.33.220:5000")
    print("🔧 Debug mode: ON")
    print("🌐 CORS Enabled for React frontend")
    print("⏳ Starting server...")
    print("="*60 + "\n")
    
    # Force flush output
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    app.run(host='0.0.0.0', port=5000, debug=True)