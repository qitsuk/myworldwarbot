import math
import time
import random
from datetime import date, timedelta
from data_loader import load_countries, load_events
from world import World
from conflict import Conflict, PYRRHIC_RATIO
from alliance import Alliance
from logger import log

VOWELS = set('aeiouAEIOU')

TIMESCALE_TEST = 0.5
TIMESCALE_PROD = 1 * 60 * 60  # 1 hours per month

INVASION_THRESHOLD = 10.0
ALLIANCE_CHANCE       = 0.002  # chance per month an unaligned country seeks an alliance
ALLIANCE_DECAY_CHANCE = 0.008  # chance per member per month to defect
MAX_ALLIANCE_SIZE     = 6      # hard cap on members per alliance

PEACETIME_ARMY_BASE   = 0.012  # minimum standing army: 1.2% of population
PEACETIME_ARMY_SCALE  = 0.04   # each point of world.risk adds this × population to the target
WARTIME_ARMY_TARGET   = 0.40   # nations mobilise toward 40% of military_cap during war
RECRUITMENT_RATE      = 0.04   # close 4% of the gap to target each month
DEBUG = False

PEACE_MONTHS      = 42    # no wars for the first 3.5 years
RAMP_MONTHS       = 24    # risk ramps 0 → BASE_RISK over the following 2 years
BASE_RISK         = 0.15
RISK_ESCALATION   = 0.0004  # risk grows by this much per month after the ramp ends
MAX_RISK          = 0.70    # hard ceiling
STALEMATE_MONTHS  = 36    # if no new conflict starts in this many months, force one

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

GIANT_PERCENTILE = 0.15   # top 15% by military_cap are giants; they cannot ally

def get_giant_threshold(world):
    caps = sorted(c.military_cap for c in world.countries)
    idx  = int(len(caps) * (1 - GIANT_PERCENTILE))
    return caps[max(idx, 0)]

def form_alliances(world):
    giant_threshold = get_giant_threshold(world)
    at_war_set = {c.attacker for c in world.active_conflicts} | {c.defender for c in world.active_conflicts}

    for country in list(world.countries):
        if get_alliance(country, world):
            continue
        if country.military_cap >= giant_threshold:
            continue
        if country in at_war_set:
            continue
        if random.random() > ALLIANCE_CHANCE:
            continue

        # Existing alliances this country could join (not full, no giants, not at war with any member)
        joinable = [
            a for a in world.alliances
            if len(a.members) < MAX_ALLIANCE_SIZE
            and all(m.military_cap < giant_threshold for m in a.members)
            and not any(m in at_war_set for m in a.members)
            and not any(
                (c.attacker == country and c.defender in a.members) or
                (c.attacker in a.members and c.defender == country)
                for c in world.active_conflicts
            )
        ]

        # Unaligned non-giant countries this country could partner with
        unaligned = [
            c for c in world.countries
            if not get_alliance(c, world)
            and c != country
            and c.military_cap < giant_threshold
            and c not in at_war_set
            and not any(
                (cf.attacker == country and cf.defender == c) or
                (cf.attacker == c and cf.defender == country)
                for cf in world.active_conflicts
            )
        ]

        if not joinable and not unaligned:
            continue

        # Weight alliances by size × avg member strength (safety in numbers),
        # weight unaligned candidates by their military_cap
        options  = joinable + unaligned
        weights  = (
            [len(a.members) * (sum(m.military_cap for m in a.members) / len(a.members)) + 1
             for a in joinable] +
            [c.military_cap + 1 for c in unaligned]
        )
        chosen = random.choices(options, weights=weights, k=1)[0]

        if isinstance(chosen, Alliance):
            chosen.members.append(country)
            log(f"  [ALLIANCE] {country.name} joins the {chosen.name}!")
        else:
            world.alliances.append(Alliance([country, chosen]))
            log(f"  [ALLIANCE] {country.name} and {chosen.name} have formed an alliance!")

def decay_alliances(world):
    """Each month, members may defect from their alliance."""
    for alliance in list(world.alliances):
        # Prune members no longer in the world
        for member in list(alliance.members):
            if member not in world.countries:
                alliance.remove_member(member)

        for member in list(alliance.members):
            if random.random() > ALLIANCE_DECAY_CHANCE:
                continue
            old_name = alliance.name
            alliance.remove_member(member)
            log(f"  [ALLIANCE] {member.name} withdraws from {old_name}.")

        if len(alliance.members) < 2 and alliance in world.alliances:
            world.alliances.remove(alliance)

def check_final_war(world):
    """If every surviving nation is in an alliance, fracture them and force the final war."""
    if len(world.countries) <= 1 or world.active_conflicts:
        return
    # If any nation is unallied, war can start naturally — nothing to do
    if any(get_alliance(c, world) is None for c in world.countries):
        return

    log("  [WORLD] Only allied nations remain. The grand alliance fractures!")
    world.alliances.clear()

    # Pair nations by military strength and start conflicts
    remaining = sorted(world.countries, key=lambda c: c.military_strength, reverse=True)
    paired = set()
    for i, a in enumerate(remaining):
        if a in paired:
            continue
        for b in remaining[i + 1:]:
            if b in paired:
                continue
            world.active_conflicts.append(Conflict(a, b))
            log(f"  >> {a.name} turns on former ally {b.name}!")
            paired.add(a)
            paired.add(b)
            break
    # Any unpaired nation (odd count) attacks the strongest
    for c in remaining:
        if c not in paired:
            world.active_conflicts.append(Conflict(c, remaining[0]))
            log(f"  >> {c.name} turns on former ally {remaining[0].name}!")

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
    if secondary not in world.countries or primary not in world.countries:
        return
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
        'world_population': sum(c.population for c in world.countries),
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
        if random.random() < 0.04:
            event = random.choice(non_combat_events)

            # Each event rolls its own severity: 60%–140% of the base impact
            severity = random.uniform(0.6, 1.4)
            econ_hit = event.economy_impact * severity
            mil_hit  = event.military_impact * severity
            # Population impacts are dampened — events disrupt growth, not kill millions.
            # Wars and disasters handle real casualties separately.
            pop_hit  = event.population_impact * severity * 0.25

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

    # War exhaustion decays over time — nations gradually recover their appetite for conflict
    for country in world.countries:
        if country.war_exhaustion > 0:
            country.war_exhaustion = max(0.0, country.war_exhaustion - 0.04)

    # Natural population growth (annual rate applied monthly)
    # Nations at war skip growth — civilian casualties in Conflict handle their population
    at_war_countries = {c.attacker for c in world.active_conflicts} | {c.defender for c in world.active_conflicts}
    for country in world.countries:
        if country not in at_war_countries:
            country.population = int(country.population * (1 + country.population_growth / 12))

    # Military recruitment: nations build toward a target force size each month
    for country in world.countries:
        if country in at_war_countries:
            # Wartime mobilisation: draft toward a large fraction of theoretical cap
            target = int(country.military_cap * WARTIME_ARMY_TARGET)
        else:
            # Peacetime: standing army scales with global tension
            # At risk=0: 1.2% of pop. At risk=0.70: ~4% of pop.
            tension_target = PEACETIME_ARMY_BASE + world.risk * PEACETIME_ARMY_SCALE
            target = int(country.population * tension_target)
        target = min(target, country.military_cap)
        if country.military_strength < target:
            recruit = max(1, int((target - country.military_strength) * RECRUITMENT_RATE))
            country.military_strength = min(country.military_strength + recruit, country.military_cap)

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
            winner, loser = conflict.winner, conflict.loser

            # War exhaustion: both sides become less likely to start new conflicts.
            # Scales with duration — longer wars leave nations more drained.
            exhaustion = min(0.75, 0.10 + conflict.duration_days * 0.008)
            if winner:
                winner.war_exhaustion = min(1.0, winner.war_exhaustion + exhaustion * 0.6)
            if loser:
                loser.war_exhaustion  = min(1.0, loser.war_exhaustion  + exhaustion)

            if conflict.peace_deal == 'merger':
                # Negotiated union — both names blend, full resource transfer
                alliance = get_alliance(winner, world)
                merge_countries(winner, loser, world)
                if alliance and alliance in world.alliances:
                    world.alliances.remove(alliance)

            elif conflict.peace_deal == 'annexation':
                # Unconditional surrender — winner's name survives, full resources
                annexe(winner, loser, world)

            else:
                # Military defeat — if winner refused a peace offer, pyrrhic penalty applies
                if conflict.pyrrhic:
                    loser.economy    = int(loser.economy    * PYRRHIC_RATIO)
                    loser.population = max(1, int(loser.population * PYRRHIC_RATIO))
                    loser.nukes      = int(loser.nukes      * PYRRHIC_RATIO)
                    log(f"  [PEACE] A pyrrhic victory — {winner.name} inherits the ruins of {loser.name}.")
                annexe(winner, loser, world)

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
        attack_chance = base_probability * strength_ratio * world.risk * nuclear_deterrence * (1.0 - country.war_exhaustion)

        if random.random() < attack_chance:
            if strength_ratio >= INVASION_THRESHOLD:
                # The underdog gets a chance to resist based on their tech advantage
                tech_factor   = target.tech_level / max(country.tech_level, 0.1)
                resist_chance = min(0.80, 0.35 * tech_factor)
                if random.random() < resist_chance:
                    if tech_factor > 1.1:
                        log(f"  >> {target.name} refuses to surrender — their superior technology gives them courage!")
                    else:
                        log(f"  >> {target.name} refuses to surrender despite overwhelming odds!")
                    conflict = Conflict(country, target)
                    world.active_conflicts.append(conflict)
                    trigger_alliance_support(country, target, world)
                else:
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

    decay_alliances(world)
    form_alliances(world)
    check_final_war(world)

def _update_risk(current_day, current_risk):
    if current_day <= PEACE_MONTHS:
        return 0.0
    if current_day <= PEACE_MONTHS + RAMP_MONTHS:
        t = (current_day - PEACE_MONTHS) / RAMP_MONTHS
        return round(BASE_RISK * t, 4)
    # Post-ramp: risk creeps up slowly, representing mounting global tension
    extra = (current_day - PEACE_MONTHS - RAMP_MONTHS) * RISK_ESCALATION
    return min(MAX_RISK, round(BASE_RISK + extra, 4))

def main():
    log("Loading world data...")
    countries = load_countries()
    events = load_events()

    world = World(
        stability=1.0,
        risk=0.0,
        countries=countries
    )

    log(f"World initialized with {len(world.countries)} countries.")
    log(f"Simulation start date: {START_DATE.strftime('%B %d, %Y')}")
    log("Starting simulation...\n")

    last_conflict_month = PEACE_MONTHS  # tracks when a conflict last broke out

    running = True
    while running:
        world.current_day += 1
        date_str = current_date(world).strftime("%B %d, %Y")

        world.risk = _update_risk(world.current_day, world.risk)

        if world.current_day == PEACE_MONTHS + 1:
            log(f"  [WORLD] The peace is over. Nations begin to mobilise.")
        elif world.current_day == PEACE_MONTHS + RAMP_MONTHS + 1:
            log(f"  [WORLD] Global tensions have reached a breaking point.")

        conflicts_before = len(world.active_conflicts)
        simulate_day(world, events)
        if len(world.active_conflicts) > conflicts_before:
            last_conflict_month = world.current_day

        # Stalemate breaker: if no new war has started in world.stalemate_months, force one
        if (world.risk >= BASE_RISK
                and not world.active_conflicts
                and len(world.countries) > 1
                and world.current_day - last_conflict_month >= world.stalemate_months):
            candidates = sorted(world.countries, key=lambda c: c.military_strength, reverse=True)
            aggressor = candidates[0]
            target    = random.choice(candidates[1:])
            log(f"  [WORLD] A long peace breeds ambition. {aggressor.name} grows restless and strikes {target.name}!")
            world.active_conflicts.append(Conflict(aggressor, target))
            trigger_alliance_support(aggressor, target, world)
            last_conflict_month = world.current_day

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
