"""
Development:  python server.py
Production:   pip install eventlet
              gunicorn --worker-class eventlet -w 1 server:app
"""
import os
import random
import threading
from collections import deque
import logger
import main as sim
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from data_loader import load_countries, load_events
from world import World

load_dotenv(Path(__file__).parent / '.env')

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


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def on_connect():
    global _sim_started
    with _state_lock:
        if _last_state:
            emit('state', _last_state)
        for msg in _log_buffer:
            emit('log', {'message': msg})
    with _sim_lock:
        if not _sim_started:
            _sim_started = True
            socketio.start_background_task(_run_simulation)


def _run_simulation():
    global _last_state
    import time

    def emit_log(msg):
        with _state_lock:
            _log_buffer.append(msg)
        socketio.emit('log', {'message': msg})

    logger.set_emit(emit_log)

    countries = load_countries()
    events = load_events()
    world = World(stability=1.0, risk=0.0, countries=countries)

    logger.log(f'World initialized with {len(world.countries)} countries.')
    logger.log(f'Simulation start: {sim.START_DATE.strftime("%B %d, %Y")}')
    logger.log('Starting simulation...')
    logger.log(f'[STARTUP] A new simulation is starting! {len(world.countries)} nations, beginning {sim.START_DATE.strftime("%B %Y")}. Timescale: {_fmt_timescale(sim.sleep_time)}.')

    last_conflict_month = sim.PEACE_MONTHS
    _tension_thresholds = {
        0.25: "Tensions are rising across the globe.",
        0.40: "The world is on edge — conflicts grow more frequent.",
        0.55: "A global conflict seems inevitable.",
        0.70: "The world stands on the brink of total war.",
    }
    _tension_seen = set()

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
        sim.simulate_day(world, events)
        if len(world.active_conflicts) > conflicts_before:
            last_conflict_month = world.current_day

        # Stalemate breaker
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

        state = sim.get_world_state(world)
        with _state_lock:
            _last_state = state
        socketio.emit('state', state)

        time.sleep(sim.sleep_time)

    if world.countries:
        winner = world.countries[0].name
        months = world.current_day
        flavor = random.choice(_GAMEOVER_FLAVORS).format(winner=winner, years=months // 12)
        logger.log(f'SIMULATION OVER — {flavor}')
        socketio.emit('gameover', {
            'winner': winner,
            'months': months,
            'years': months // 12,
        })


if __name__ == '__main__':
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    socketio.run(app, host='0.0.0.0', port=5000, debug=debug)
