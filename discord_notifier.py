"""
Discord webhook notifier.
Set the DISCORD_WEBHOOK_URL environment variable to enable.
Toggle individual event types in NOTIFY_EVENTS below.
"""

import json
import os
import threading
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

# Toggle which event types get posted to Discord
NOTIFY_EVENTS = {
    'war':        True,   # >> war declarations and instant conquests
    'nuclear':    True,   # [NUCLEAR] strikes
    'peace':      True,   # [PEACE] deals, mergers, surrenders
    'union':      True,   # [UNION] nation mergers
    'world':      True,   # [WORLD] tension milestones, stalemate breaks
    'alliance':   True,   # [ALLIANCE] formations
    'defection':  True,   # [ALLIANCE] member withdrawals / fractures
    'gameover':   True,   # simulation over
    'startup':    True,   # simulation starting up
}

# Embed colours (decimal)
_COLOURS = {
    'war':        0xE05252,   # red
    'nuclear':    0xFF6600,   # orange
    'peace':      0x57C757,   # green
    'union':      0x58A6FF,   # blue
    'world':      0xA371F7,   # purple
    'alliance':   0x8B949E,   # grey
    'defection':  0xE07B39,   # amber
    'gameover':   0xFFD700,   # gold
    'startup':    0x3FB950,   # green
}

_TITLES = {
    'war':        '⚔️ War',
    'nuclear':    '☢️ Nuclear Strike',
    'peace':      '🕊️ Peace',
    'union':      '🤝 Union',
    'world':      '🌍 World Event',
    'alliance':   '🛡️ Alliance Formed',
    'defection':  '🏳️ Alliance Broken',
    'gameover':   '🏆 Simulation Over',
    'startup':    '🌐 New Simulation Starting',
}


def _classify(message: str) -> str | None:
    m = message.strip()
    if '[NUCLEAR]'  in m: return 'nuclear'
    if '[WORLD]'    in m: return 'world'
    if '[UNION]'    in m: return 'union'
    if '[PEACE]'    in m: return 'peace'
    if '[STARTUP]'  in m: return 'startup'
    if '[ALLIANCE]' in m: return 'defection' if 'withdraws' in m else 'alliance'
    if m.startswith('>>'):  return 'war'
    if 'SIMULATION OVER' in m.upper(): return 'gameover'
    return None


def _build_payload(event_type: str, message: str) -> bytes:
    clean = message.strip().lstrip('> ').strip()
    payload = {
        'embeds': [{
            'title':       _TITLES[event_type],
            'description': f"{clean}\n\n[🗺️ View the live map](https://worldwarbot.qitsuk.dk)",
            'color':       _COLOURS[event_type],
	    'url':	   'https://worldwarbot.qitsuk.dk',
	    'footer': {
		'text': 'Visit https://worldwarbot.qitsuk.dk to see the full, current world map'
	    }
        }]
    }
    return json.dumps(payload).encode()


def _post(event_type: str, message: str) -> None:
    try:
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=_build_payload(event_type, message),
            headers={
		'Content-Type': 'application/json',
		'User-Agent': 'DiscordBot (https://worldwarbot.qitsuk.dk, 1.0)'
		},
            method='POST',
        )
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as e:
        print(f"[NOTIFY ERROR] HTTP {e.code}: {e.reason}")
    except Exception as e:
        print(f"[NOTIFY ERROR] {e}")


def notify(message: str) -> None:
    """Call this for every log line. Filters and dispatches asynchronously."""
    print(f'[NOTIFY] called with {message[:80]}')
    if not WEBHOOK_URL:
        return
    event_type = _classify(message)
    if event_type is None:
        return
    if not NOTIFY_EVENTS.get(event_type, False):
        return
    # Fire-and-forget — never block the simulation thread
    threading.Thread(target=_post, args=(event_type, message), daemon=True).start()
