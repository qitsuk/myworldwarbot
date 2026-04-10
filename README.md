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

### 1. Deploy the application

```bash
git clone <your-repo-url> ~/worldwarbot
# or copy files manually:
# cp -r . ~/worldwarbot/
```

### 2. Set up the Python environment

```bash
cd ~/worldwarbot
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install flask flask-socketio eventlet gunicorn
```

### 3. Set production mode

In `~/worldwarbot/main.py`, set:

```python
DEBUG = False
```

This switches the simulation from test speed (0.5s/tick) to production speed (3 hours/tick).

---

## Systemd Service

Create `~/.config/systemd/user/worldwarbot.service`:

```bash
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/worldwarbot.service
```

```ini
[Unit]
Description=World War Simulation
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/worldwarbot
ExecStart=%h/worldwarbot/venv/bin/gunicorn \
    --worker-class eventlet \
    --workers 1 \
    --bind 127.0.0.1:8765 \
    --timeout 120 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile %h/worldwarbot/logs/access.log \
    --error-logfile %h/worldwarbot/logs/error.log \
    server:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

> **Important:** Gunicorn must use exactly `--workers 1`. Socket.IO holds simulation state in memory — multiple workers will each run their own simulation and clients will get inconsistent state.

Enable and start:

```bash
mkdir -p ~/worldwarbot/logs

systemctl --user daemon-reload
systemctl --user enable worldwarbot
systemctl --user start worldwarbot

# Check it started cleanly
systemctl --user status worldwarbot
journalctl --user -u worldwarbot -f
```

---

## Caddy Configuration

Add a site block to your `/etc/caddy/Caddyfile`:

```caddy
warbot.yourdomain.com {
    reverse_proxy 127.0.0.1:8765 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}

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

## Discord Notifications

### 1. Create a webhook

In your Discord server: **Channel Settings → Integrations → Webhooks → New Webhook**.
Copy the webhook URL.

### 2. Set the environment variable

Add it to the service file so it's available at runtime. Edit `~/.config/systemd/user/worldwarbot.service` and add under `[Service]`:

```ini
Environment="DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
```

Then reload:

```bash
systemctl --user daemon-reload
systemctl --user restart worldwarbot
```

### 3. Configure which events get posted

In `discord_notifier.py`, toggle the `NOTIFY_EVENTS` dict:

```python
NOTIFY_EVENTS = {
    'war':      True,   # ⚔️  war declarations and conquests
    'nuclear':  True,   # ☢️  nuclear strikes
    'peace':    True,   # 🕊️  peace deals, mergers, surrenders
    'union':    True,   # 🤝  nation mergers
    'world':    True,   # 🌍  tension milestones, stalemate breaks
    'alliance': False,  # 🛡️  alliance formations and defections (chatty)
    'gameover': True,   # 🏆  simulation over
}
```

No webhook URL set = Discord silently disabled, simulation unaffected.

---

## Managing the Simulation

```bash
# View live logs
journalctl --user -u worldwarbot -f

# Restart (starts a fresh simulation)
systemctl --user restart worldwarbot

# Stop
systemctl --user stop worldwarbot

# View access log
tail -f ~/worldwarbot/logs/access.log
```

---

## Updating

```bash
cd ~/worldwarbot
git pull
systemctl --user restart worldwarbot
```

---

## Notes

- Each simulation run is entirely in-memory. Restarting the service starts a **fresh simulation** from the beginning.
- The simulation runs at **3 hours per in-game month** in production. A full run may take days or weeks of real time.
