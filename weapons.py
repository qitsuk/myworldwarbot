"""
weapons.py — Special weapons metadata, constants, and initialisation helpers.
"""

import math
import random

WEAPON_KEYS = [
    'cyber', 'drones', 'hypersonic', 'emp', 'neutron',
    'ai_combat', 'shield', 'kinetic', 'orbital_laser', 'nano', 'tectonic',
]

# Full display names for the UI
WEAPON_NAMES = {
    'cyber':        'Cyberweapons',
    'drones':       'Drone Swarms',
    'hypersonic':   'Hypersonic Missiles',
    'emp':          'EMP Strike',
    'neutron':      'Neutron Bombs',
    'ai_combat':    'AI Combat Systems',
    'shield':       'Directed Energy Defence',
    'kinetic':      'Orbital Kinetic Impactors',
    'orbital_laser':'Orbital Laser Platform',
    'nano':         'Nanoweapons',
    'tectonic':     'Tectonic Weapons',
}

# Tier, year gate, tech gate
WEAPONS = {
    'cyber':        {'tier': 1, 'year_gate': 2030, 'tech_gate': 2.0, 'type': 'passive'},
    'drones':       {'tier': 1, 'year_gate': 2035, 'tech_gate': 2.5, 'type': 'consumed'},
    'hypersonic':   {'tier': 1, 'year_gate': 2040, 'tech_gate': 2.8, 'type': 'consumed'},
    'emp':          {'tier': 1, 'year_gate': 2042, 'tech_gate': 3.0, 'type': 'consumed'},
    'neutron':      {'tier': 2, 'year_gate': 2052, 'tech_gate': 3.5, 'type': 'consumed'},
    'ai_combat':    {'tier': 2, 'year_gate': 2055, 'tech_gate': 3.5, 'type': 'passive'},
    'shield':       {'tier': 2, 'year_gate': 2058, 'tech_gate': 3.5, 'type': 'passive'},
    'kinetic':      {'tier': 3, 'year_gate': 2070, 'tech_gate': 4.0, 'type': 'consumed'},
    'orbital_laser':{'tier': 3, 'year_gate': 2075, 'tech_gate': 4.5, 'type': 'passive'},
    'nano':         {'tier': 3, 'year_gate': 2085, 'tech_gate': 4.5, 'type': 'consumed'},
    'tectonic':     {'tier': 3, 'year_gate': 2095, 'tech_gate': 5.0, 'type': 'consumed'},
}

BASE_RESEARCH_RATE = 0.005  # per month — tier-1 takes ~8 yrs for avg nation, tier-3 20+ yrs


def _economy_factor(country):
    gdp_per_capita = country.economy / max(country.population, 1)
    return max(0.2, min(2.0, (gdp_per_capita / 10_000) ** 0.5))


def advance_research(country, current_year, world_alliances):
    """
    Advance research progress for all weapons by one month.
    Returns nothing — mutates country in place.
    """
    ef = _economy_factor(country)

    # Build alliance bonus map once
    alliance_has_researched = {}
    for key in WEAPON_KEYS:
        alliance_has_researched[key] = False

    for alliance in world_alliances:
        if not any(m is country for m in alliance.members):
            continue
        for ally in alliance.members:
            if ally is country:
                continue
            for key in WEAPON_KEYS:
                if ally.research[key] >= 1.0:
                    alliance_has_researched[key] = True

    for key in WEAPON_KEYS:
        if country.research[key] >= 1.0:
            continue
        spec = WEAPONS[key]
        year_gate = spec['year_gate']
        tech_gate = spec['tech_gate']

        year_factor = max(0.05, min(1.0, 1.0 + (current_year - year_gate) / 25.0))
        tech_factor = min(1.0, country.tech_level / tech_gate)
        alliance_bonus = 1.25 if alliance_has_researched[key] else 1.0

        rate = BASE_RESEARCH_RATE * year_factor * tech_factor * ef * alliance_bonus
        country.research[key] = min(1.0, country.research[key] + rate)


def build_stockpiles(country, uranium_per_nuke):
    """
    Build weapon stockpiles for one month (called after research == 1.0 checks).
    Mutates country in place.
    """
    ef = _economy_factor(country)

    # Drones — cap halved; build rate halved
    if country.research['drones'] >= 1.0:
        country.drones = min(500, country.drones + round(ef * 1.5))

    # Hypersonic — cap halved; build rate halved
    if country.research['hypersonic'] >= 1.0:
        country.hypersonic = min(80, country.hypersonic + round(ef * 0.5))

    # EMP — cap more than halved; build rate halved
    if country.research['emp'] >= 1.0:
        inc = max(0, round(ef * 0.25))
        country.emp_arsenal = min(12, country.emp_arsenal + inc)

    # Neutron (requires uranium) — costs more uranium; cap reduced
    if country.research['neutron'] >= 1.0:
        cost_per_bomb = uranium_per_nuke * 1.2   # was 0.6 — now comparable to a real warhead
        if country.uranium >= cost_per_bomb:
            n = min(1, int(country.uranium / cost_per_bomb))
            country.uranium -= n * cost_per_bomb
            country.neutron_bombs = min(60, country.neutron_bombs + n)

    # Kinetic — build chance more than halved; cap halved
    if country.research['kinetic'] >= 1.0:
        if random.random() < ef * 0.06:
            country.kinetic_impactors = min(8, country.kinetic_impactors + 1)

    # Nano — build rate halved; cap less than halved
    if country.research['nano'] >= 1.0:
        country.nano_arsenal = min(35, country.nano_arsenal + round(ef * 0.4))

    # Tectonic — build chance significantly reduced
    if country.research['tectonic'] >= 1.0:
        if random.random() < ef * 0.008:
            country.tectonic_arsenal = min(1, country.tectonic_arsenal + 1)

    # Passive levels — all build rates reduced ~30-40%
    if country.research['cyber'] >= 1.0:
        country.cyber_level = min(1.0, country.cyber_level + ef * 0.002)

    if country.research['ai_combat'] >= 1.0:
        country.ai_combat_level = min(1.0, country.ai_combat_level + ef * 0.002)

    if country.research['shield'] >= 1.0:
        country.shield_level = min(1.0, country.shield_level + ef * 0.0015)

    if country.research['orbital_laser'] >= 1.0:
        country.orbital_laser_level = min(1.0, country.orbital_laser_level + ef * 0.0015)
        if country.orbital_laser_level >= 0.8:
            # One charge per month once nearly maxed out; cap 2 so it never floods
            country.orbital_laser_charges = min(2, country.orbital_laser_charges + 1)


def _starting_stockpile(country, key, uranium_per_nuke):
    """Give a country a modest starting stockpile (~12 months of production at new rates)."""
    ef = _economy_factor(country)

    if key == 'drones':
        country.drones = min(500, round(ef * 1.5 * 12))
    elif key == 'hypersonic':
        country.hypersonic = min(80, round(ef * 0.5 * 12))
    elif key == 'emp':
        country.emp_arsenal = min(12, max(1, round(ef * 0.25 * 12)))
    elif key == 'neutron':
        country.neutron_bombs = min(60, max(1, round(ef * 0.5 * 12)))
    elif key == 'kinetic':
        country.kinetic_impactors = min(8, max(1, round(ef * 0.06 * 12)))
    elif key == 'nano':
        country.nano_arsenal = min(35, round(ef * 0.4 * 12))
    elif key == 'tectonic':
        country.tectonic_arsenal = 1 if random.random() < ef * 0.15 else 0
    elif key == 'cyber':
        country.cyber_level = min(1.0, ef * 0.002 * 12)
    elif key == 'ai_combat':
        country.ai_combat_level = min(1.0, ef * 0.002 * 12)
    elif key == 'shield':
        country.shield_level = min(1.0, ef * 0.0015 * 12)
    elif key == 'orbital_laser':
        country.orbital_laser_level = min(1.0, ef * 0.0015 * 12)
        if country.orbital_laser_level >= 0.8:
            country.orbital_laser_charges = min(2, 1)


def init_country_weapons(country, start_year, uranium_per_nuke=6.0):
    """
    Set initial research / stockpile values for a country at simulation start.
    If start_year > weapon year_gate AND country.tech_level >= weapon tech_gate,
    set research to 1.0 immediately and give a starting stockpile.
    """
    for key in WEAPON_KEYS:
        spec = WEAPONS[key]
        if start_year > spec['year_gate'] and country.tech_level >= spec['tech_gate']:
            country.research[key] = 1.0
        else:
            country.research[key] = 0.0
