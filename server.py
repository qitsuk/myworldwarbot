"""
Development:  python server.py
Production:   pip install eventlet
              gunicorn --worker-class eventlet -w 1 server:app
"""
import os
import re
import random
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, send_file, jsonify, abort
from flask_socketio import SocketIO, emit
import logger
import main as sim
from data_loader import load_countries, load_events, DATA_YEAR
from world import World

# Regex patterns to extract winner name from each gameover flavor
_WINNER_PATTERNS = [
    r'After \d+ years of struggle, (.+?) stands alone',
    r'^(.+?) has done the impossible',
    r'The last flag standing belongs to (.+?)\.',
    r'History ends and begins again — (.+?) reigns supreme',
    r'From the ashes of a hundred nations, (.+?) emerges victorious',
    r'The world has known nothing but war for \d+ years\. Now it knows only (.+?)\.',
    r'One nation to rule them all: (.+?) claims the world',
    r'The struggle is over\. (.+?) is the last nation',
    r'After \d+ years and countless wars, (.+?) stands as the sole',
    r'The simulation ends as it must — with one\. (.+?) has conquered the world',
]

load_dotenv(Path(__file__).parent / '.env')

LOGS_DIR = Path(__file__).parent / 'logs'

_GAMEOVER_FLAVORS = [
    "After {years} years of struggle, {winner} stands alone — master of the world.",
    "{winner} has done the impossible: conquered the entire world in {years} years.",
    "The last flag standing belongs to {winner}. The world falls silent.",
    "History ends and begins again — {winner} reigns supreme after {years} years of war.",
    "From the ashes of a hundred nations, {winner} emerges victorious.",
    "The world has known nothing but war for {years} years. Now it knows only {winner}.",
    "One nation to rule them all: {winner} claims the world after {years} years.",
    "The struggle is over. {winner} is the last nation on Earth.",
    "After {years} years and countless wars, {winner} stands as the sole world power.",
    "The simulation ends as it must — with one. {winner} has conquered the world.",
]


def _fmt_timescale(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds}s per month (test mode)"
    if seconds < 60:
        return f"{int(seconds)} seconds per month"
    if seconds < 3600:
        mins = seconds / 60
        return f"{mins:.0f} minute{'s' if mins != 1 else ''} per month"
    hours = seconds / 3600
    return f"{hours:.4g} hour{'s' if hours != 1 else ''} per month"


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ww-sim-2032')
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

_sim_lock = threading.Lock()
_state_lock = threading.Lock()
_sim_started = False
_last_state = None
_log_buffer = deque(maxlen=200)  # rolling history replayed to new clients
_current_log_path = None         # Path to the active run's log file


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download-log')
def download_log():
    """Download the full log of the currently running (or most recent) simulation."""
    # Prefer the active run's log
    if _current_log_path and _current_log_path.exists():
        return send_file(
            str(_current_log_path),
            as_attachment=True,
            download_name=_current_log_path.name,
            mimetype='text/plain',
        )
    # Fall back to the most recently modified log in the logs directory
    if LOGS_DIR.exists():
        logs = sorted(LOGS_DIR.glob('sim_*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            return send_file(
                str(logs[0]),
                as_attachment=True,
                download_name=logs[0].name,
                mimetype='text/plain',
            )
    abort(404)


@app.route('/logs')
def list_logs():
    """Return a JSON list of all stored simulation logs, newest first."""
    if not LOGS_DIR.exists():
        return jsonify([])
    logs = sorted(LOGS_DIR.glob('sim_*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
    return jsonify([
        {
            'name': p.name,
            'size_kb': round(p.stat().st_size / 1024, 1),
            'modified': datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'url': f'/logs/{p.name}',
        }
        for p in logs
    ])


@app.route('/logs/<filename>')
def serve_log(filename):
    """Download a specific past simulation log by filename."""
    # Sanitise: only allow simple filenames, no path traversal
    if '/' in filename or '\\' in filename or not filename.startswith('sim_'):
        abort(400)
    path = LOGS_DIR / filename
    if not path.exists():
        abort(404)
    return send_file(str(path), as_attachment=True, download_name=filename, mimetype='text/plain')


@app.route('/winners')
def get_winners():
    """Return the last 5 simulation winners parsed from log files."""
    if not LOGS_DIR.exists():
        return jsonify([])
    logs = sorted(LOGS_DIR.glob('sim_*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
    winners = []
    for log_path in logs:
        if len(winners) >= 5:
            break
        try:
            start_year = int(log_path.stem.split('_')[1])
        except (IndexError, ValueError):
            start_year = None
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            continue
        winner_name = None
        years = None
        stats = {}
        for line in reversed(lines):
            line = line.strip()
            if line.startswith('SIMULATION STATS'):
                for key in ('start_pop', 'end_pop', 'mil_casualties', 'civ_casualties', 'nukes_used'):
                    m = re.search(rf'{key}:(\d+)', line)
                    if m:
                        stats[key] = int(m.group(1))
            elif line.startswith('SIMULATION WINNER — '):
                winner_name = line[len('SIMULATION WINNER — '):]
            elif line.startswith('SIMULATION OVER'):
                flavor = line[len('SIMULATION OVER — '):]
                if not winner_name:
                    for pat in _WINNER_PATTERNS:
                        m = re.search(pat, flavor)
                        if m:
                            winner_name = m.group(1)
                            break
                years_m = re.search(r'(\d+) years', flavor)
                years = int(years_m.group(1)) if years_m else None
            if winner_name and ('start_pop' in stats or not stats):
                break
        if winner_name:
            winners.append({
                'winner': winner_name,
                'years': years,
                'start_year': start_year,
                'completed': datetime.fromtimestamp(log_path.stat().st_mtime).strftime('%Y-%m-%d'),
                'start_pop': stats.get('start_pop'),
                'end_pop': stats.get('end_pop'),
                'mil_casualties': stats.get('mil_casualties'),
                'civ_casualties': stats.get('civ_casualties'),
                'nukes_used': stats.get('nukes_used'),
            })
    return jsonify(winners)


VERSION = '2.2.3'

# ── Socket ────────────────────────────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    global _sim_started
    emit('version', {'version': VERSION})
    with _state_lock:
        if _last_state:
            emit('state', _last_state)
        for msg in _log_buffer:
            emit('log', {'message': msg})
    with _sim_lock:
        if not _sim_started:
            _sim_started = True
            socketio.start_background_task(_run_simulation)


# ── Simulation ────────────────────────────────────────────────────────────────

def _run_simulation():
    global _last_state, _current_log_path
    import time

    # Create logs directory and open this run's log file
    LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    _current_log_path = LOGS_DIR / f'sim_{sim.START_YEAR}_{ts}.log'
    log_file = _current_log_path.open('w', encoding='utf-8')

    def emit_log(msg):
        with _state_lock:
            _log_buffer.append(msg)
        log_file.write(msg + '\n')
        log_file.flush()
        socketio.emit('log', {'message': msg})

    logger.set_emit(emit_log)

    countries = load_countries(start_year=sim.START_YEAR)
    events = load_events()
    world = World(stability=1.0, risk=0.0, countries=countries)
    world.start_population = sum(c.population for c in world.countries)

    years_extrapolated = sim.START_YEAR - DATA_YEAR
    logger.log(f'World initialized with {len(world.countries)} countries.')
    logger.log(f'Simulation start: {sim.START_DATE.strftime("%B %d, %Y")} ({years_extrapolated} years extrapolated from {DATA_YEAR})')
    logger.log('Starting simulation...')
    logger.log(f'[STARTUP] A new simulation is starting! {len(world.countries)} nations in {sim.START_YEAR}, extrapolated {years_extrapolated} years from {DATA_YEAR}. Timescale: {_fmt_timescale(sim.sleep_time)}.')

    last_conflict_month = sim.PEACE_MONTHS
    first_war_started   = sim.DEBUG    # in debug mode act as if war already started (no timescale switch)
    current_sleep       = sim.sleep_time if sim.DEBUG else sim.peace_sleep_time
    _tension_thresholds = {
        0.25: "Tensions are rising across the globe.",
        0.40: "The world is on edge — conflicts grow more frequent.",
        0.55: "A global conflict seems inevitable.",
        0.70: "The world stands on the brink of total war.",
    }
    _tension_seen = set()

    try:
        while len(world.countries) > 1:
            world.current_day += 1
            date_str = sim.current_date(world).strftime('%B %d, %Y')
            logger.log(f'--- {date_str} ---')

            world.risk = sim._update_risk(world.current_day, world.risk)

            if world.current_day == sim.PEACE_MONTHS + 1:
                logger.log(f'  [WORLD] {random.choice(sim._WORLD_PEACE_ENDS_FLAVORS)}')
            elif world.current_day == sim.PEACE_MONTHS + sim.RAMP_MONTHS + 1:
                logger.log(f'  [WORLD] {random.choice(sim._WORLD_TENSIONS_PEAK_FLAVORS)}')

            for threshold, msg in _tension_thresholds.items():
                if world.risk >= threshold and threshold not in _tension_seen:
                    _tension_seen.add(threshold)
                    logger.log(f'  [TENSION] {msg}')

            conflicts_before = len(world.active_conflicts)

            # Non-war simulation: economy, tech, diplomacy, new war declarations
            sim.simulate_day(world, events, skip_war=True)

            # Stalemate breaker (runs after diplomacy, before combat sub-ticks)
            if (world.risk >= sim.BASE_RISK
                    and not world.active_conflicts
                    and len(world.countries) > 1
                    and world.current_day - last_conflict_month >= world.stalemate_months):
                from conflict import Conflict
                candidates = sorted(world.countries, key=lambda c: c.military_strength, reverse=True)
                aggressor  = candidates[0]
                target     = random.choice(candidates[1:])
                flavor = random.choice(sim._STALEMATE_FLAVORS).format(aggressor=aggressor.name, target=target.name)
                logger.log(f'  [WORLD] {flavor}')
                world.active_conflicts.append(Conflict(aggressor, target))
                sim.trigger_alliance_support(aggressor, target, world)
                last_conflict_month = world.current_day

            # Timescale switch: first war detected this month
            if len(world.active_conflicts) > conflicts_before:
                last_conflict_month = world.current_day
                if not first_war_started:
                    first_war_started = True
                    current_sleep     = sim.sleep_time
                    logger.log(f'  [STARTUP] First conflict detected — switching to real timescale ({_fmt_timescale(sim.sleep_time)}).')

            # ── War sub-ticks ──────────────────────────────────────────────────
            # Combat advances in WAR_SUBTICKS equal steps spread across the tick
            # interval, so the front-line dot animates smoothly during the month.
            sub_sleep = current_sleep / sim.WAR_SUBTICKS
            for _ in range(sim.WAR_SUBTICKS):
                countries_before = len(world.countries)
                sim.step_wars(world)

                # Drain strikes generated during this sub-tick
                from cities import fallout_duration_months
                for strike in world.pending_strikes:
                    launcher_name, target_name = strike[0], strike[1]
                    city_name   = strike[2] if len(strike) > 2 else None
                    city_lat    = strike[3] if len(strike) > 3 else None
                    city_lon    = strike[4] if len(strike) > 4 else None
                    used        = strike[5] if len(strike) > 5 else None
                    weapon_type = strike[6] if len(strike) > 6 else 'nuke'

                    if weapon_type in ('kinetic', 'laser', 'tectonic'):
                        socketio.emit('weapon_strike', {
                            'type':     weapon_type,
                            'launcher': launcher_name,
                            'target':   target_name,
                            'city':     city_name,
                            'lat':      city_lat,
                            'lon':      city_lon,
                            'day':      world.current_day,
                        })
                    else:
                        warheads_used = used or 1
                        expires = world.current_day + fallout_duration_months(warheads_used)
                        if weapon_type == 'nuke':
                            world.nuked_cities.append({
                                'lat': city_lat, 'lon': city_lon,
                                'city': city_name or target_name, 'country': target_name,
                                'launcher': launcher_name,
                                'warheads': warheads_used,
                                'expires': expires,
                            })
                        socketio.emit('nuclear_strike', {
                            'type':     weapon_type,
                            'launcher': launcher_name,
                            'target':   target_name,
                            'city':     city_name,
                            'lat':      city_lat,
                            'lon':      city_lon,
                            'warheads': warheads_used,
                            'expires':  expires,
                            'day':      world.current_day,
                        })
                world.pending_strikes.clear()

                socketio.emit('war_update', sim.get_war_state(world))

                # If a war ended this sub-tick, push a full state update immediately
                # so the map reflects ownership changes the moment the log announces them.
                if len(world.countries) != countries_before:
                    state = sim.get_world_state(world)
                    with _state_lock:
                        _last_state = state
                    socketio.emit('state', state)

                time.sleep(sub_sleep)

            # Full state once per month (no extra sleep — already slept current_sleep above)
            state = sim.get_world_state(world)
            with _state_lock:
                _last_state = state
            socketio.emit('state', state)

        if world.countries:
            winner = world.countries[0].name
            months = world.current_day
            end_population = sum(c.population for c in world.countries)
            flavor = random.choice(_GAMEOVER_FLAVORS).format(winner=winner, years=months // 12)
            logger.log(f'SIMULATION OVER — {flavor}')
            logger.log(f'SIMULATION WINNER — {winner}')
            logger.log(
                f'SIMULATION STATS — '
                f'start_pop:{world.start_population} '
                f'end_pop:{end_population} '
                f'mil_casualties:{world.total_military_casualties} '
                f'civ_casualties:{world.total_civilian_casualties} '
                f'nukes_used:{world.total_nukes_used}'
            )
            socketio.emit('gameover', {
                'winner': winner,
                'months': months,
                'years': months // 12,
                'nukes_used': world.total_nukes_used,
                'mil_casualties': world.total_military_casualties,
                'civ_casualties': world.total_civilian_casualties,
                'start_pop': world.start_population,
                'end_pop': end_population,
            })

    finally:
        log_file.close()


if __name__ == '__main__':
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    socketio.run(app, host='0.0.0.0', port=5000, debug=debug, allow_unsafe_werkzeug=True)
