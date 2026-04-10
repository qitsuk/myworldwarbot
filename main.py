import math
import time
import random
from datetime import date, timedelta
from data_loader import load_countries, load_events
from world import World
from conflict import Conflict
from alliance import Alliance
from logger import log

VOWELS = set('aeiouAEIOU')

TIMESCALE_TEST = 0.5
TIMESCALE_PROD = 86400 / 30

INVASION_THRESHOLD = 10.0
ALLIANCE_CHANCE = 0.002       # chance per country per month to seek an alliance
MERGE_THRESHOLD = 0.10        # both allies must be at or below 10% of military_cap to merge
DEBUG = True

START_DATE = date(2032, 1, 1)

sleep_time = TIMESCALE_TEST if DEBUG else TIMESCALE_PROD

def current_date(world):
    """Each simulation tick = 1 month. Returns the 1st of the corresponding month."""
    months = world.current_day - 1
    year  = START_DATE.year + (START_DATE.month - 1 + months) // 12
    month = (START_DATE.month - 1 + months) % 12 + 1
    return date(year, month, 1)

def find_absorber(dead_country, world, exclude=None):
    """Find the active country that absorbed a dead country's territories."""
    for c in world.countries:
        if c is not exclude and any(n in c.absorbed_names for n in dead_country.absorbed_names):
            return c
    return None

def annexe(winner, loser, world):
    if loser not in world.countries:
        return

    # If winner was already eliminated this same tick, redirect to whoever absorbed them
    if winner not in world.countries:
        winner = find_absorber(winner, world, exclude=loser)
        if winner is None:
            # No absorber found — just remove the loser silently
            world.countries.remove(loser)
            return

    winner.economy += loser.economy
    winner.population += loser.population
    winner.territory += loser.territory
    winner.neighbors = list(set(winner.neighbors + loser.neighbors) - {winner.name})
    winner.military_strength = min(winner.military_strength, winner.military_cap)
    winner.absorbed_names.extend(loser.absorbed_names)
    winner.nukes += loser.nukes
    winner.nuked = winner.nuked or loser.nuked
    world.countries.remove(loser)
    log(f"  >> {winner.name} has annexed {loser.name}!")

    # Clean loser out of any alliance
    for alliance in list(world.alliances):
        if alliance.has_member(loser):
            alliance.remove_member(loser)
            if len(alliance.members) < 2:
                world.alliances.remove(alliance)

def blend_country_names(a, b):
    """Create a portmanteau from two country names (e.g. Pakistan + Afghanistan = Pakighanistan)."""
    # Take ~1/4 of A, extended forward to end on a vowel
    cut_a = max(2, len(a) // 4)
    for i in range(cut_a, min(len(a) - 1, cut_a + 4)):
        if a[i] in VOWELS:
            cut_a = i + 1
            break

    # Start ~1/4 into B, adjusted to begin on a consonant
    cut_b = max(1, len(b) // 4)
    for i in range(cut_b, min(len(b) - 1, cut_b + 3)):
        if b[i] not in VOWELS:
            cut_b = i
            break

    pa, pb = a[:cut_a], b[cut_b:]

    # Avoid duplicate consonants at the junction (e.g. "Fr" + "rmany" → "Frmany")
    if pa and pb and pa[-1].lower() == pb[0].lower() and pa[-1].lower() not in VOWELS:
        pb = pb[1:]

    result = pa + pb
    return result[0].upper() + result[1:] if result else ''

def get_valid_neighbors(country, world):
    existing_names = {c.name for c in world.countries}
    return [c for c in world.countries if c.name in country.neighbors and c.name in existing_names]

def get_targets(country, world):
    valid = get_valid_neighbors(country, world)
    if valid:
        return valid
    others = [c for c in world.countries if c != country]
    return random.sample(others, min(3, len(others)))

def get_alliance(country, world):
    for alliance in world.alliances:
        if alliance.has_member(country):
            return alliance
    return None

def form_alliances(world):
    for country in list(world.countries):
        if get_alliance(country, world):
            continue

        if random.random() > ALLIANCE_CHANCE:
            continue

        candidates = [
            c for c in get_valid_neighbors(country, world)
            if not get_alliance(c, world) and c != country
        ]
        if not candidates:
            continue

        partner = random.choice(candidates)

        at_war = any(
            (c.attacker == country and c.defender == partner) or
            (c.attacker == partner and c.defender == country)
            for c in world.active_conflicts
        )
        if at_war:
            continue

        alliance = Alliance([country, partner])
        world.alliances.append(alliance)
        log(f"  [ALLIANCE] {country.name} and {partner.name} have formed an alliance!")

def trigger_alliance_support(attacker, defender, world):
    alliance = get_alliance(defender, world)
    if not alliance:
        return
    for ally in alliance.get_allies(defender):
        if ally not in world.countries:
            continue
        already_fighting = any(
            c.attacker == ally or c.defender == ally
            for c in world.active_conflicts
        )
        if already_fighting:
            continue
        conflict = Conflict(ally, attacker)
        world.active_conflicts.append(conflict)
        log(f"  [ALLIANCE] {ally.name} enters the war in defence of {defender.name}!")

def merge_countries(primary, secondary, world):
    old_name = primary.name
    merged_name = blend_country_names(primary.name, secondary.name)
    primary.name = merged_name
    primary.economy += secondary.economy
    primary.population += secondary.population
    primary.territory += secondary.territory
    primary.neighbors = list(set(primary.neighbors + secondary.neighbors) - {merged_name})
    primary.military_strength = min(
        primary.military_strength + secondary.military_strength,
        primary.military_cap
    )
    primary.absorbed_names.extend(secondary.absorbed_names)
    primary.nukes += secondary.nukes
    primary.nuked = primary.nuked or secondary.nuked
    primary.tech_level = round(max(primary.tech_level, secondary.tech_level), 2)
    world.countries.remove(secondary)
    log(f"  [UNION] {old_name} and {secondary.name} have unified into {merged_name}!")

def check_merges(world):
    for alliance in list(world.alliances):
        members = [c for c in alliance.members if c in world.countries]
        if len(members) < 2:
            continue

        all_critical = all(
            c.military_strength <= c.military_cap * MERGE_THRESHOLD
            for c in members
        )
        if not all_critical:
            continue

        any_fighting = any(
            any(c.attacker == m or c.defender == m for c in world.active_conflicts)
            for m in members
        )
        if any_fighting:
            continue

        primary = max(members, key=lambda c: c.military_strength)
        for other in [m for m in members if m is not primary]:
            merge_countries(primary, other, world)

        world.alliances.remove(alliance)

def get_world_state(world):
    at_war_names = set()
    for c in world.active_conflicts:
        at_war_names.add(c.attacker.name)
        at_war_names.add(c.defender.name)

    alliance_id_map = {}
    for i, alliance in enumerate(world.alliances):
        for member in alliance.members:
            alliance_id_map[member.name] = i

    top5 = sorted(world.countries, key=lambda c: c.military_strength, reverse=True)[:5]

    # territory_info: original country name → {color, owner name, at war, in alliance}
    # This lets the frontend color absorbed territories with the annexing country's color.
    territory_info = {}
    for country in world.countries:
        entry = {
            'c': country.color,
            'o': country.name,
            'w': country.name in at_war_names,
            'a': country.name in alliance_id_map,
        }
        for orig_name in country.absorbed_names:
            territory_info[orig_name] = entry

    return {
        'day': world.current_day,
        'date': current_date(world).strftime('%B %d, %Y'),
        'total_countries': len(world.countries),
        'countries': [
            {
                'name': c.name,
                'military': int(c.military_strength),
                'military_cap': int(c.military_cap),
                'economy': int(c.economy),
                'population': int(c.population),
                'at_war': c.name in at_war_names,
                'alliance_id': alliance_id_map.get(c.name),
                'absorbed_names': c.absorbed_names,
                'nukes': c.nukes,
                'nuked': c.nuked,
                'tech_level': round(c.tech_level, 2),
            }
            for c in world.countries
        ],
        'conflicts': [
            {
                'attacker': c.attacker.name,
                'defender': c.defender.name,
                'day': c.duration_days,
            }
            for c in world.active_conflicts
        ],
        'alliances': [
            [m.name for m in a.members]
            for a in world.alliances
        ],
        'top5': [
            {
                'name': c.name,
                'military': int(c.military_strength),
                'military_cap': int(c.military_cap),
                'color': c.color,
                'nukes': c.nukes,
            }
            for c in top5
        ],
        'territory_info': territory_info,
    }

def print_status(world):
    if world.active_conflicts:
        log(f"  Active conflicts ({len(world.active_conflicts)}):")
        for c in world.active_conflicts:
            log(f"    {c.attacker.name} ({int(c.attacker.military_strength):,}) vs {c.defender.name} ({int(c.defender.military_strength):,}) - Month {c.duration_days}")

    if world.current_day % 12 == 0:
        log(f"\n  Top 5 countries by military strength:")
        top = sorted(world.countries, key=lambda c: c.military_strength, reverse=True)[:5]
        for c in top:
            log(f"    {c.name}: {int(c.military_strength):,} troops, economy {int(c.economy):,}, tech {c.tech_level:.1f}")

        if world.alliances:
            log(f"\n  Active alliances ({len(world.alliances)}):")
            for a in world.alliances:
                log(f"    {a.name}")
        log("")

def apply_events(world, events):
    non_combat_events = [e for e in events if e.type not in ("invasion", "war")]
    for country in world.countries:
        if random.random() < 0.1:
            event = random.choice(non_combat_events)

            # Each event rolls its own severity: 60%–140% of the base impact
            severity = random.uniform(0.6, 1.4)
            econ_hit = event.economy_impact * severity
            mil_hit  = event.military_impact * severity
            pop_hit  = event.population_impact * severity

            country.economy = max(0, int(country.economy * (1 + econ_hit)))
            country.military_strength = max(0, int(country.military_strength * (1 + mil_hit)))
            country.military_strength = min(country.military_strength, country.military_cap)
            country.population = max(1, int(country.population * (1 + pop_hit)))

            flavor = random.choice(event.flavor) if event.flavor else ""

            impacts = []
            if econ_hit != 0:
                sign = "+" if econ_hit > 0 else ""
                impacts.append(f"Economy {sign}{econ_hit * 100:.0f}%")
            if mil_hit != 0:
                sign = "+" if mil_hit > 0 else ""
                impacts.append(f"Military {sign}{mil_hit * 100:.0f}%")
            if pop_hit != 0:
                sign = "+" if pop_hit > 0 else ""
                impacts.append(f"Population {sign}{pop_hit * 100:.0f}%")
            impact_str = f" [{', '.join(impacts)}]" if impacts else ""

            log(f"  [EVENT] {country.name} - {event.name}: {flavor}{impact_str}")

def simulate_day(world, events):
    apply_events(world, events)

    # Tech growth: each month, nations edge toward their GDP-per-capita tech target.
    # Logarithmic and uncapped — a wealthy empire keeps advancing indefinitely.
    # Tech only ever improves; annexing poorer nations never regresses your R&D.
    for country in world.countries:
        gdp_per_capita = country.economy / max(country.population, 1)
        target_tech = 1.0 + 2.0 * math.log10(1 + gdp_per_capita / 500)
        if target_tech > country.tech_level:
            country.tech_level = round(country.tech_level + (target_tech - country.tech_level) * 0.03, 2)

    for conflict in list(world.active_conflicts):
        conflict.simulate_day(len(world.countries), world.endgame_nuke_threshold)
        if conflict.is_over:
            world.active_conflicts.remove(conflict)
            annexe(conflict.winner, conflict.loser, world)

    for country in list(world.countries):
        targets = get_targets(country, world)
        if not targets:
            continue

        target = random.choice(targets)

        already_at_war = any(
            (c.attacker == country or c.defender == country or
             c.attacker == target or c.defender == target)
            for c in world.active_conflicts
        )
        if already_at_war:
            continue

        strength_ratio = country.military_strength / max(target.military_strength, 1)
        base_probability = next((e.base_probability for e in events if e.type == "invasion"), 0.01)

        # Nuclear deterrence: each warhead tier halves willingness to attack
        nuclear_deterrence = 1.0 / (1.0 + 0.5 * (target.nukes / 100) ** 0.5) if target.nukes > 0 else 1.0
        attack_chance = base_probability * strength_ratio * world.risk * nuclear_deterrence

        if random.random() < attack_chance:
            if strength_ratio >= INVASION_THRESHOLD:
                log(f"  >> {country.name} invades {target.name} and conquers them instantly!")
                annexe(country, target, world)
            else:
                conflict = Conflict(country, target)
                world.active_conflicts.append(conflict)
                log(f"  >> {country.name} declares war on {target.name}!")
                trigger_alliance_support(country, target, world)

    # Nuclear proliferation: wealthy non-nuclear nations may secretly develop nukes
    for country in list(world.countries):
        if country.nukes == 0 and country.economy >= 500_000_000_000:
            proliferation_chance = (country.economy / 1e13) * 0.0001
            if random.random() < proliferation_chance:
                country.nukes = random.randint(1, 5)
                log(f"  [NUCLEAR] \u2622 {country.name} has secretly developed nuclear weapons!")

    check_merges(world)
    form_alliances(world)

def main():
    log("Loading world data...")
    countries = load_countries()
    events = load_events()

    world = World(
        stability=1.0,
        risk=0.15,
        countries=countries
    )

    log(f"World initialized with {len(world.countries)} countries.")
    log(f"Simulation start date: {START_DATE.strftime('%B %d, %Y')}")
    log("Starting simulation...\n")

    running = True
    while running:
        world.current_day += 1
        date_str = current_date(world).strftime("%B %d, %Y")

        simulate_day(world, events)

        log(f"{date_str} - {len(world.countries)} countries remaining")
        print_status(world)

        time.sleep(sleep_time)

        if len(world.countries) <= 1:
            date_str = current_date(world).strftime("%B %d, %Y")
            log(f"\nSimulation over! {world.countries[0].name} conquered the world on {date_str}!")
            log(f"Total simulation time: {world.current_day} months ({world.current_day // 12} years, {world.current_day % 12} months)")
            running = False

if __name__ == "__main__":
    main()
