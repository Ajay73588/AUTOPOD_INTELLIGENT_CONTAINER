# 🚀 AutoPod: Intelligent Container Lifecycle Manager

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Podman](https://img.shields.io/badge/Podman-Automation-success.svg)
![Flask](https://img.shields.io/badge/Flask-Backend-lightgrey.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite3-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

AutoPod is an **intelligent, automated container lifecycle manager** built using **Python, Flask, Podman, and SQLite**.  
It automates code deployment by pulling the latest code from GitHub, rebuilding the container, and restarting it — triggered automatically via **GitHub Webhooks**.

---

## 🧠 Key Features

- ⚙️ **Fully Automated CI/CD Deployment** with GitHub Webhooks
- 🐳 **Podman-based Container Build, Stop & Run Management**
- 🔁 **Automatic Sync with SQLite Database**
- 📊 **Interactive Dashboard** to monitor container status and logs
- 🧩 **Simple Flask API Integration**
- 💡 **Lightweight and Easy to Deploy**

---

## 🧩 System Workflow

| Step | Developer Action                | AutoPod Action                                    |
| ---- | ------------------------------- | ------------------------------------------------- |
| 1️⃣   | Developer pushes code to GitHub | Webhook triggers AutoPod                          |
| 2️⃣   | —                               | AutoPod receives webhook event                    |
| 3️⃣   | —                               | Pulls the latest code using `git pull`            |
| 4️⃣   | —                               | Builds a new **Podman image**                     |
| 5️⃣   | —                               | Stops any running container (if exists)           |
| 6️⃣   | —                               | Starts a **new container** with the updated code  |
| 7️⃣   | —                               | Logs the entire process and updates the dashboard |

---

## 🧱 Architecture Diagram

```plaintext
     ┌─────────────────────────────┐
     │         GitHub Repo         │
     │   (Code Push / Commit)      │
     └──────────────┬──────────────┘
                    │ Webhook (JSON)
                    ▼
         ┌────────────────────────────┐
         │       AutoPod Server       │
         │   (Flask + Podman + DB)    │
         └──────────────┬─────────────┘
                        │
                        ▼
         ┌────────────────────────────┐
         │      Podman Engine         │
         │  Builds / Runs Containers  │
         └──────────────┬─────────────┘
                        │
                        ▼
         ┌────────────────────────────┐
         │   SQLite Database (Logs)   │
         │   + HTML Dashboard UI      │
         └────────────────────────────┘
```
