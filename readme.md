AutoPod
 A lightweight automation platform for managing Podman containers, designed for developers to streamline local container lifecycle management.

 ## Features
 - Automatically rebuilds and restarts containers on code changes.
 - GitHub webhook integration for real-time updates.
 - Simple dashboard for container status and logs.
 - Containerized Flask service with SQLite backend.

 ## Setup
 1. Install Podman: `sudo apt install podman`
 2. Clone this repository: `git clone https://github.com/your-username/AutoPod.git`
 3. Build and run: `podman build -t autopod:latest . && podman run -d -p 5000:5000 autopod:latest`
 4. Configure a GitHub webhook to `http://<your-host>:5000/webhook`.

 ## Usage
 Access the dashboard at `http://<your-host>:5000` to monitor containers and logs.
