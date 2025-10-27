import os
import logging
from logging.handlers import RotatingFileHandler
import json
from flask import Flask, render_template, jsonify, request
from webhook_handler import handle_webhook
from podman_manager import PodmanManager
from database import init_db, get_container_logs, get_container_status
import atexit
from database import close_db_connection

app = Flask(__name__)

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
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.route('/')
def dashboard():
    """Render the main dashboard page."""
    return render_template('dashboard.html')

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

@app.route('/api/sync', methods=['POST'])
def api_sync():
    """API endpoint to manually sync Podman containers with database."""
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
            return jsonify({"success": False, "error": "PodmanManager not initialized"}), 500
        
        containers = podman.get_containers()
        logger.info(f"Fetched {len(containers)} raw containers from Podman")
        return jsonify({"success": True, "data": containers})
    except Exception as e:
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

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle GitHub webhook events."""
    try:
        if podman is None:
            raise RuntimeError("PodmanManager not initialized")
        
        handle_webhook(podman)
        logger.info("Webhook processed successfully")
        return {"status": "success", "message": "Webhook processed"}, 200
    except Exception as e:
        logger.exception("Webhook handling error")
        return {"status": "error", "message": str(e)}, 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "podman_initialized": podman is not None,
        "database_initialized": True
    })

# Container Management Endpoints
@app.route('/api/containers/start', methods=['POST'])
def api_start_container():
    """API endpoint to start a container."""
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
            return jsonify({"success": True, "message": f"Container {container_name} started"})
        else:
            return jsonify({"success": False, "error": f"Failed to start container {container_name}"}), 500
            
    except Exception as e:
        logger.exception("Error starting container")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/containers/stop', methods=['POST'])
def api_stop_container():
    """API endpoint to stop a container."""
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
            return jsonify({"success": True, "message": f"Container {container_name} stopped"})
        else:
            return jsonify({"success": False, "error": f"Failed to stop container {container_name}"}), 500
            
    except Exception as e:
        logger.exception("Error stopping container")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/containers/restart', methods=['POST'])
def api_restart_container():
    """API endpoint to restart a container."""
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
            return jsonify({"success": True, "message": f"Container {container_name} restarted"})
        else:
            return jsonify({"success": False, "error": f"Failed to restart container {container_name}"}), 500
            
    except Exception as e:
        logger.exception("Error restarting container")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/containers/remove', methods=['POST'])
def api_remove_container():
    """API endpoint to remove a container."""
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
            return jsonify({"success": True, "message": f"Container {container_name} removed"})
        else:
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

@app.route('/api/containers/<container_name>/open', methods=['POST'])
def api_open_container_web(container_name):
    """Open container's web interface."""
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

@app.route('/api/images/pull', methods=['POST'])
def api_pull_image():
    """Pull an image from a registry."""
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

@app.route('/api/images/push', methods=['POST'])
def api_push_image():
    """Push an image to a registry."""
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

@app.route('/api/images/remove', methods=['POST'])
def api_remove_image():
    """Remove a local image."""
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

@app.route('/api/images/tag', methods=['POST'])
def api_tag_image():
    """Tag an image with a new name."""
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

if __name__ == '__main__':
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
    print("⏳ Starting server...")
    print("="*60 + "\n")
    
    # Force flush output
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
