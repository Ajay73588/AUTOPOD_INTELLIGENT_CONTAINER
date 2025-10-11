import os
import logging
import json
from flask import Flask, render_template, jsonify
from webhook_handler import handle_webhook
from podman_manager import PodmanManager
from database import init_db, get_container_logs, get_container_status

app = Flask(__name__)

# Ensure logs folder exists
os.makedirs('logs', exist_ok=True)

# Configure JSON logging
logging.basicConfig(
    filename='logs/autopod.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Podman manager and database
podman = PodmanManager()
init_db()

@app.route('/')
def dashboard():
    """Render the main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """API endpoint to get container statuses."""
    try:
        statuses = get_container_status()
        return jsonify({"success": True, "data": statuses})
    except Exception as e:
        logger.error(f"Error fetching container statuses: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logs')
def api_logs():
    """API endpoint to get container logs."""
    try:
        logs = get_container_logs()
        return jsonify({"success": True, "data": logs})
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle GitHub webhook events."""
    try:
        handle_webhook(podman)
        logger.info(json.dumps({"event": "webhook_received", "status": "success"}))
        return {"status": "success"}, 200
    except Exception as e:
        logger.error(json.dumps({"event": "webhook_error", "error": str(e)}))
        return {"status": "error", "message": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
