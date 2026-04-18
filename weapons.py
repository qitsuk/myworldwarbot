"""
weapons.py — Special weapons metadata, constants, and initialisation helpers.

Remaining weapons: Neutron Bombs, Orbital Kinetic Impactors,
                   Orbital Laser Platform, Tectonic Weapons.
"""

import math
import random

WEAPON_KEYS = [
    'neutron', 'kinetic', 'orbital_laser', 'tectonic',
]

# Full display names for the UI
WEAPON_NAMES = {
    'neutron':      'Neutron Bombs',
    'kinetic':      'Orbital Kinetic Impactors',
    'orbital_laser':'Orbital Laser Platform',
    'tectonic':     'Tectonic Weapons',
}

# Tier, year gate, tech gate
WEAPONS = {
    'neutron':      {'tier': 2, 'year_gate': 2060, 'tech_gate': 4.0, 'type': 'consumed'},
    'kinetic':      {'tier': 3, 'year_gate': 2075, 'tech_gate': 4.5, 'type': 'consumed'},
    'orbital_laser':{'tier': 3, 'year_gate': 2080, 'tech_gate': 4.5, 'type': 'passive'},
    'tectonic':     {'tier': 3, 'year_gate': 2100, 'tech_gate': 5.0, 'type': 'consumed'},
}

BASE_RESEARCH_RATE = 0.005  # per month — tier-2 takes ~10 yrs for avg nation, tier-3 20+ yrs


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
    alliance_has_researched = {key: False for key in WEAPON_KEYS}

    for alliance in world_alliances:
        if not any(m is country for m in alliance.members):
            continue
        for ally in alliance.members:
            if ally is country:
                continue
            for key in WEAPON_KEYS:
                if ally.research[key] >= 1.0:
                    alliance_has_researched[key] = True

    for i, key in enumerate(WEAPON_KEYS):
        if country.research[key] >= 1.0:
            continue
        # Must have fully researched the previous weapon first
        if i > 0 and country.research[WEAPON_KEYS[i - 1]] < 1.0:
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

    # Neutron Bombs (requires uranium)
    if country.research['neutron'] >= 1.0:
        cost_per_bomb = uranium_per_nuke * 1.2
        if country.uranium >= cost_per_bomb:
            n = min(1, int(country.uranium / cost_per_bomb))
            country.uranium -= n * cost_per_bomb
            country.neutron_bombs = min(60, country.neutron_bombs + n)

    # Kinetic Impactors — low build chance; cap 8
    if country.research['kinetic'] >= 1.0:
        if random.random() < ef * 0.06:
            country.kinetic_impactors = min(8, country.kinetic_impactors + 1)

    # Orbital Laser Platform — passive level + charges
    if country.research['orbital_laser'] >= 1.0:
        country.orbital_laser_level = min(1.0, country.orbital_laser_level + ef * 0.0015)
        if country.orbital_laser_level >= 0.8:
            # One charge per month once nearly maxed; cap 2
            country.orbital_laser_charges = min(2, country.orbital_laser_charges + 1)

    # Tectonic Weapons — very rare build
    if country.research['tectonic'] >= 1.0:
        if random.random() < ef * 0.008:
            country.tectonic_arsenal = min(1, country.tectonic_arsenal + 1)


def _starting_stockpile(country, key, uranium_per_nuke):
    """Give a country a modest starting stockpile (~12 months of production)."""
    ef = _economy_factor(country)

    if key == 'neutron':
        country.neutron_bombs = min(60, max(1, round(ef * 0.5 * 12)))
    elif key == 'kinetic':
        country.kinetic_impactors = min(8, max(1, round(ef * 0.06 * 12)))
    elif key == 'orbital_laser':
        country.orbital_laser_level = min(1.0, ef * 0.0015 * 12)
        if country.orbital_laser_level >= 0.8:
            country.orbital_laser_charges = min(2, 1)
    elif key == 'tectonic':
        country.tectonic_arsenal = 1 if random.random() < ef * 0.15 else 0


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
            _starting_stockpile(country, key, uranium_per_nuke)
        else:
            country.research[key] = 0.0
