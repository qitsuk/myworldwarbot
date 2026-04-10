# World War Simulation — Deployment Guide

## Overview

Flask + Flask-SocketIO application served by Gunicorn (eventlet worker) behind Caddy.

---

## Prerequisites

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
```

---

## Installation

### 1. Create a dedicated user

```bash
sudo useradd -r -s /bin/false -d /opt/worldwarbot worldwarbot
```

### 2. Deploy the application

```bash
sudo mkdir -p /opt/worldwarbot
sudo git clone <your-repo-url> /opt/worldwarbot
# or copy files manually:
# sudo cp -r . /opt/worldwarbot/
sudo chown -R worldwarbot:worldwarbot /opt/worldwarbot
```

### 3. Set up the Python environment

```bash
cd /opt/worldwarbot
sudo -u worldwarbot python3 -m venv venv
sudo -u worldwarbot venv/bin/pip install --upgrade pip
sudo -u worldwarbot venv/bin/pip install flask flask-socketio eventlet gunicorn
```

### 4. Set production mode

In `/opt/worldwarbot/main.py`, set:

```python
DEBUG = False
```

This switches the simulation from test speed (0.5s/tick) to production speed (3 hours/tick).

---

## Systemd Service

Create `/etc/systemd/system/worldwarbot.service`:

```ini
[Unit]
Description=World War Simulation
After=network.target

[Service]
Type=simple
User=worldwarbot
Group=worldwarbot
WorkingDirectory=/opt/worldwarbot
ExecStart=/opt/worldwarbot/venv/bin/gunicorn \
    --worker-class eventlet \
    --workers 1 \
    --bind 127.0.0.1:8765 \
    --timeout 120 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile /var/log/worldwarbot/access.log \
    --error-logfile /var/log/worldwarbot/error.log \
    server:app
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=worldwarbot

[Install]
WantedBy=multi-user.target
```

> **Important:** Gunicorn must use exactly `--workers 1`. Socket.IO holds simulation state in memory — multiple workers will each run their own simulation and clients will get inconsistent state.

Set up the log directory and enable the service:

```bash
sudo mkdir -p /var/log/worldwarbot
sudo chown worldwarbot:worldwarbot /var/log/worldwarbot

sudo systemctl daemon-reload
sudo systemctl enable worldwarbot
sudo systemctl start worldwarbot

# Check it started cleanly
sudo systemctl status worldwarbot
sudo journalctl -u worldwarbot -f
```

---

## Caddy Configuration

Add a site block to your `/etc/caddy/Caddyfile`:

```caddy
warbot.yourdomain.com {
    reverse_proxy 127.0.0.1:8765 {
        # Required for Socket.IO long-polling and WebSocket upgrade
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}

        # Keep connections alive for WebSocket
        transport http {
            keepalive 30s
            keepalive_idle_conns 10
        }
    }
}
```

Reload Caddy:

```bash
sudo systemctl reload caddy
```

Caddy v2 handles WebSocket upgrades automatically — no extra configuration needed for Socket.IO.

---

## Managing the Simulation

```bash
# View live logs
sudo journalctl -u worldwarbot -f

# Restart (starts a fresh simulation)
sudo systemctl restart worldwarbot

# Stop
sudo systemctl stop worldwarbot

# View Gunicorn access log
sudo tail -f /var/log/worldwarbot/access.log
```

---

## Updating

```bash
cd /opt/worldwarbot
sudo -u worldwarbot git pull
sudo systemctl restart worldwarbot
```

---

## Notes

- Each simulation run is entirely in-memory. Restarting the service starts a **fresh simulation** from the beginning.
- The simulation runs at **3 hours per in-game month** in production. A full run (until one nation conquers the world) may take days or weeks of real time.
- If you want to watch it from another machine on your network before pointing a domain at it, you can temporarily bind to `0.0.0.0:8765` and access it directly.
