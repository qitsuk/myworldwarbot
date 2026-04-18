# World War Simulation — Deployment Guide

## Overview

Flask + Flask-SocketIO application served by Gunicorn (eventlet worker) behind Caddy.

---

## Changelog

### v1.6 — White Peace & Proximity-Based War Targeting
- **White peace**: any war can now end with a mutual ceasefire and full withdrawal — no territory, resources, or concessions change hands; both sides get peace treaty protection and war exhaustion; previously only possible between evenly matched nations
- **Proximity-based war targeting**: nations now strongly prefer attacking nearby countries; target weight decays continuously with distance (`1 / (1 + dist_km / 1500)`) so a border neighbour is ~5× more likely to be attacked than a nation 5 000 km away; direct neighbours retain an additional 3× bonus on top

### v1.5 — Streamlined Weapons, War Pacing & Nuclear Realism (Next war will be this one)
- **Nuclear de-escalation removed**: no more forced global disarmament treaty on first nuclear strike — nations keep their arsenals and the simulation runs its full course
- **Special weapons cut from 11 → 4**: removed Cyberweapons, Drone Swarms, Hypersonic Missiles, EMP Strike, AI Combat Systems, Directed Energy Defence, and Nanoweapons; kept only **Neutron Bombs**, **Orbital Kinetic Impactors**, **Orbital Laser Platform**, and **Tectonic Weapons**
- **Weapons re-gated**: Neutron Bombs year 2060 / tech 4.0; Kinetic Impactors year 2075 / tech 4.5; Orbital Laser year 2080 / tech 4.5; Tectonic Weapons year 2100 / tech 5.0 — none available in the first 30–50 years of simulation
- **Minimum 3-month war duration**: no war can end (by peace deal or military collapse) before 3 in-game months have passed, regardless of military size disparity
- **Increased peace willingness**: `PEACE_OFFER_CHANCE` 15%→25%, `LOSER_ACCEPT_CHANCE` 60%→72%, `SURRENDER_CHANCE` 9%→15%, `WINNER_ACCEPT_SURRENDER` 55%→65%, `WINNER_CEASEFIRE_CHANCE` 50%→60%; peace thresholds raised so offers come earlier in a war
- **Nuclear salvo spreading**: when a nation fires ≥ 5 warheads, they are now distributed across multiple cities (1 city per 3 warheads, up to 10 cities), weighted by city population — 1300 warheads no longer land on a single city; damage compounds independently per city
- **Missile shield (Iron Dome mechanic)**: all nations passively develop missile defence, with research rate proportional to world tension and economy — once any nuke is ever fired, research triples as governments divert budget; max 85% interception at full level; shield level shown in country tooltip

### v1.4 — Simulation Longevity, Weapon Scarcity & Bug Fixes (Currently running)
- **Gradual nuclear disarmament**: when the first nuke fires, nations phase down their arsenals at 18%/month (~18 months to near-zero) rather than all vanishing instantly; rogue states (8–30% chance, higher for large arsenals) secretly retain 10–30% of their warheads and hold that floor permanently
- **Rogue nuke use**: nukes flagged as retained by rogue states can still be fired in combat even after the disarmament treaty
- **Ceasefire peace treaties**: after a ceasefire both parties are blocked from re-declaring war for 30 months; previously winners could immediately re-invade the same tick
- **War exhaustion increased**: base exhaustion after a war raised from 0.10→0.20; winner penalty scaled up; ceasefires impose heavier exhaustion (0.35/0.65) to discourage quick revenge campaigns
- **Annexation devastation**: conquering nation only receives 82% of the loser's economy, population, and territory — war damage is now modelled rather than a free 100% transfer
- **Special weapons made scarce**: `BASE_RESEARCH_RATE` cut from 0.008→0.005/month (tier-1 ~8 yrs avg, tier-3 20+ yrs); all stockpile build rates and caps roughly halved; neutron bomb uranium cost doubled (now comparable to a real warhead); orbital laser capped at 2 charges; alliance research bonus reduced 1.5×→1.25×; starting stockpiles cut from 24 months → 12 months of production
- **Front-line battle dot fix**: dot was frozen at the arc midpoint in test mode because the 9 500 ms D3 transition was constantly interrupted by 83 ms subtick updates; replaced with D3 `.join()` + immediate attribute setting; CSS `transition: cx/cy 0.6s` now handles smooth tracking at any tick rate
- **Initial dot position**: new conflicts now show a slight displacement based on current strength ratio instead of always centering at t=0.5
- **Git hygiene**: untracked `__pycache__/` and `.claude/settings.local.json` (caused dirty working tree on server pull); `.gitignore` updated with `*.pyc`/`*.pyo` patterns

### v1.3 — Special Weapons, Peace Deals & Nuclear Disarmament
- **11 future special weapons** across three tiers: Cyberweapons, Drone Swarms, Hypersonic Missiles, EMP Strike, Neutron Bombs, AI Combat Systems, Directed Energy Defence, Orbital Kinetic Impactors, Orbital Laser Platform, Nanoweapons, Tectonic Weapons
- Weapons are **soft year+tech gated** — research starts slowly before the gate year and accelerates past it
- **Alliance tech sharing**: members slowly converge toward the highest tech level; the tech leader also gains a bonus per ally (incentive for both sides)
- **Alliance research bonus**: 1.5× research speed if any ally has already fully researched a weapon
- Nations must **build stockpiles** over time; no free starting weapons even if the tech is pre-researched
- **Weapon combat effects**: drones boost effective strength, EMP disables enemy weapons, orbital kinetic impactors devastate garrisons, orbital laser fires charges, tectonic weapons cause catastrophic collateral damage, neutron bombs deployed by desperate nations
- **Three new peace mechanics**: winner-initiated peace offer, loser-initiated surrender (winner chooses annexation/ceasefire/rejection), and nuclear coercion (desperate nuclear power threatens; winner backs down or faces a warning strike)
- **Ceasefire outcome**: both nations survive; loser cedes 22% economy and 15% territory; war exhaustion applied to both
- **Casus belli system**: being attacked raises your probability of striking back 3× when able
- **Nuclear disarmament treaty**: the first nuclear strike ever fired triggers a global emergency pact — all arsenals zeroed, enrichment halted permanently, and all nations receive a research boost as they pivot to other weapons
- **Hall of Fame fix**: unambiguous `SIMULATION WINNER` log line replaces fragile regex parsing of flavor text
- Simulation always **starts in 2030** (first age gate); `BASE_RISK` raised to 0.25; peace period shortened to 2 years
- Country tooltip panel now shows **weapon research %** and stockpile levels for all special weapons

### v1.2 — War Animation & Visual Polish
- **Sub-tick war simulation**: combat advances in 6 sub-steps per month so the front-line dot animates smoothly
- Smooth front-line dot movement with easing between positions
- Live war statistics panel (casualties, front movement)
- Dim non-highlighted country borders when a country is selected
- Fallout zone halo rendered on the map around nuclear strike sites
- Fallout badge appears instantly on nuclear strike (no wait for next state push)
- Instant map sync on annexation — ownership updates the moment the log announces it

### v1.1 — Nuclear Improvements & Small Nations
- Small nations can now act as aggressors; nuclear first-strike mechanic added
- Hover tooltip on nuclear fallout badges showing strike details
- Overhauled nuclear damage model: city-scale population density instead of national average
- Track and display total nuclear warheads used in the Hall of Fame

### v1.0 — Hall of Fame, War Statistics & Balance of Power
- **Hall of Fame**: tracks winners across simulation runs, parsed from log files
- World population counter displayed on map overlay
- War casualty tracking (military and civilian) shown in end-of-run stats
- **Balance-of-power / hegemon mechanic**: when one nation dominates militarily, others form anti-hegemon coalitions
- Country log-hover highlighting (later removed in v1.2)

### v0.9 — Nuclear Proliferation & Enrichment
- Gradual uranium enrichment system: nations accumulate uranium over months before converting to warheads
- Nuclear panic escalation: desperate nations are more likely to launch as they approach defeat
- Animated nuclear strike visuals on the map
- Cities data (`cities.py`) used for realistic strike targeting
- Removed internal territory borders after annexation
- Persistent per-run server-side logging with downloadable log files

### v0.8 — Territory Garrisons & Fallout Badges
- Territory conquest overhauled to use per-territory garrisons; wars can capture individual territories before ending
- Nuclear fallout badges rendered on map after strikes
- Replay nuclear strike animation when hovering a log entry
- Various nuclear proliferation balance fixes (lower risk threshold, faster enrichment)

### v0.7 — War Arcs, Map Zoom & Flavor Text
- War arc visualisation connecting warring nations on the map
- Battle-front indicator dot on war arcs
- Map zoom and pan
- Extensive flavor text for world events, tension milestones, war declarations
- World tension UI showing global risk level
- Discord notification improvements; startup message with timescale info

### v0.6 — Logging, Discord & Production Setup
- Log history replayed to clients on connect (no missed events on page load)
- `.env` file for all secrets and configuration (Discord webhook, timescale, secret key)
- `TIMESCALE` environment variable for runtime speed control
- Discord notifier with configurable event categories
- `.env` loading fix when running as a systemd service

### v0.5 — Randomised Start Year & Extrapolation
- Start year randomised across a wide range; country stats (population, economy, military) extrapolated forward from the data year to match
- Basic alliance system

### v0.4 — Simulation Balancing
- Significant rebalancing of war outcomes, military strength scaling, and economic growth
- Improved war probability and targeting logic

### v0.3 — Web Interface
- Flask + SocketIO web interface with a live world map (SVG)
- Real-time log feed streamed to browser
- Country tooltip showing basic stats on hover

### v0.2 — Initial Web Port
- Ported simulation from CLI to web server
- Basic country rendering on map

### v0.1 — Initial Commit
- Text-based world war simulation: countries, military strength, economy, neighbours, war declarations, annexation, alliances

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
