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

if __name__ == '__main__':
    # Perform initial sync when starting the application
    if podman:
        try:
            logger.info("Performing initial sync on startup...")
            podman.sync_with_db()
            logger.info("Initial sync completed on startup")
        except Exception as e:
            logger.error(f"Initial sync failed: {e}")
    
    # Use debug=True for development only
    app.run(host='0.0.0.0', port=5000, debug=True)