import os
import logging
import json
from flask import Flask, render_template
from webhook_handler import handle_webhook
from podman_manager import PodmanManager
from database import init_db, get_container_logs, get_container_status

app = Flask(__name__)

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
    """Render the dashboard with container statuses and logs."""
    statuses = get_container_status()
    logs = get_container_logs()
    return render_template('dashboard.html', statuses=statuses, logs=logs)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming GitHub webhook events."""
    try:
        handle_webhook(podman)
        logger.info(json.dumps({"event": "webhook_received", "status": "success"}))
        return {"status": "success"}, 200
    except Exception as e:
        logger.error(json.dumps({"event": "webhook_error", "error": str(e)}))
        return {"status": "error", "message": str(e)}, 500

if __name__ == '__main__':
    os.makedirs('logs', exist_ok=True)
    app.run(host='0.0.0.0', port=5000)