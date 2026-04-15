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

BASE_RESEARCH_RATE = 0.008  # per month


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
        alliance_bonus = 1.5 if alliance_has_researched[key] else 1.0

        rate = BASE_RESEARCH_RATE * year_factor * tech_factor * ef * alliance_bonus
        country.research[key] = min(1.0, country.research[key] + rate)


def build_stockpiles(country, uranium_per_nuke):
    """
    Build weapon stockpiles for one month (called after research == 1.0 checks).
    Mutates country in place.
    """
    ef = _economy_factor(country)

    # Drones
    if country.research['drones'] >= 1.0:
        country.drones = min(1000, country.drones + round(ef * 3.0))

    # Hypersonic
    if country.research['hypersonic'] >= 1.0:
        country.hypersonic = min(200, country.hypersonic + round(ef * 1.0))

    # EMP
    if country.research['emp'] >= 1.0:
        inc = max(0, round(ef * 0.5))
        country.emp_arsenal = min(30, country.emp_arsenal + inc)

    # Neutron (requires uranium)
    if country.research['neutron'] >= 1.0:
        cost_per_bomb = uranium_per_nuke * 0.6
        if country.uranium >= cost_per_bomb:
            n = min(1, int(country.uranium / cost_per_bomb))
            country.uranium -= n * cost_per_bomb
            country.neutron_bombs = min(150, country.neutron_bombs + n)

    # Kinetic
    if country.research['kinetic'] >= 1.0:
        if random.random() < ef * 0.15:
            country.kinetic_impactors = min(15, country.kinetic_impactors + 1)

    # Nano
    if country.research['nano'] >= 1.0:
        country.nano_arsenal = min(80, country.nano_arsenal + round(ef * 0.8))

    # Tectonic
    if country.research['tectonic'] >= 1.0:
        if random.random() < ef * 0.02:
            country.tectonic_arsenal = min(1, country.tectonic_arsenal + 1)

    # Passive levels
    if country.research['cyber'] >= 1.0:
        country.cyber_level = min(1.0, country.cyber_level + ef * 0.003)

    if country.research['ai_combat'] >= 1.0:
        country.ai_combat_level = min(1.0, country.ai_combat_level + ef * 0.003)

    if country.research['shield'] >= 1.0:
        country.shield_level = min(1.0, country.shield_level + ef * 0.002)

    if country.research['orbital_laser'] >= 1.0:
        country.orbital_laser_level = min(1.0, country.orbital_laser_level + ef * 0.002)
        if country.orbital_laser_level >= 0.5:
            charges_gained = 2 if country.orbital_laser_level >= 1.0 else 1
            country.orbital_laser_charges = min(3, country.orbital_laser_charges + charges_gained)


def _starting_stockpile(country, key, uranium_per_nuke):
    """Give a country a reasonable starting stockpile for already-researched weapons."""
    ef = _economy_factor(country)

    if key == 'drones':
        country.drones = min(1000, round(ef * 3.0 * 24))  # ~24 months of building
    elif key == 'hypersonic':
        country.hypersonic = min(200, round(ef * 1.0 * 24))
    elif key == 'emp':
        country.emp_arsenal = min(30, max(1, round(ef * 0.5 * 24)))
    elif key == 'neutron':
        country.neutron_bombs = min(150, max(1, round(ef * 0.8 * 12)))
    elif key == 'kinetic':
        country.kinetic_impactors = min(15, max(1, round(ef * 0.15 * 12)))
    elif key == 'nano':
        country.nano_arsenal = min(80, round(ef * 0.8 * 24))
    elif key == 'tectonic':
        country.tectonic_arsenal = 1 if random.random() < ef * 0.3 else 0
    elif key == 'cyber':
        country.cyber_level = min(1.0, ef * 0.003 * 24)
    elif key == 'ai_combat':
        country.ai_combat_level = min(1.0, ef * 0.003 * 24)
    elif key == 'shield':
        country.shield_level = min(1.0, ef * 0.002 * 24)
    elif key == 'orbital_laser':
        country.orbital_laser_level = min(1.0, ef * 0.002 * 24)
        if country.orbital_laser_level >= 0.5:
            country.orbital_laser_charges = min(3, 2)


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
