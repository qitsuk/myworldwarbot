"""
Development:  python server.py
Production:   pip install eventlet
              gunicorn --worker-class eventlet -w 1 server:app
"""
import os
import random
import threading
import logger
import main as sim
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from data_loader import load_countries, load_events
from world import World

load_dotenv(Path(__file__).parent / '.env')


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


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def on_connect():
    global _sim_started
    with _state_lock:
        if _last_state:
            emit('state', _last_state)
    with _sim_lock:
        if not _sim_started:
            _sim_started = True
            socketio.start_background_task(_run_simulation)


def _run_simulation():
    global _last_state
    import time

    def emit_log(msg):
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

    while len(world.countries) > 1:
        world.current_day += 1
        date_str = sim.current_date(world).strftime('%B %d, %Y')
        logger.log(f'--- {date_str} ---')

        world.risk = sim._update_risk(world.current_day, world.risk)

        if world.current_day == sim.PEACE_MONTHS + 1:
            logger.log('  [WORLD] The peace is over. Nations begin to mobilise.')
        elif world.current_day == sim.PEACE_MONTHS + sim.RAMP_MONTHS + 1:
            logger.log('  [WORLD] Global tensions have reached a breaking point.')

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
            logger.log(f'  [WORLD] A long peace breeds ambition. {aggressor.name} grows restless and strikes {target.name}!')
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
        logger.log(f'SIMULATION OVER — {winner} has conquered the world in {months // 12} years, {months % 12} months!')
        socketio.emit('gameover', {
            'winner': winner,
            'months': months,
            'years': months // 12,
        })


if __name__ == '__main__':
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    socketio.run(app, host='0.0.0.0', port=5000, debug=debug)
