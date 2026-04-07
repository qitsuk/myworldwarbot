import time
import random
from datetime import date, timedelta
from data_loader import load_countries, load_events
from world import World
from conflict import Conflict

TIMESCALE_TEST = 0.1
TIMESCALE_PROD = 86400 / 30

INVASION_THRESHOLD = 10.0
DEBUG = True

START_DATE = date(2032, 1, 1)

sleep_time = TIMESCALE_TEST if DEBUG else TIMESCALE_PROD

def current_date(world):
    return START_DATE + timedelta(days=world.current_day - 1)

def annexe(winner, loser, world):
    if loser not in world.countries:
        return
    winner.economy += loser.economy
    winner.population += loser.population
    winner.territory += loser.territory
    winner.neighbors = list(set(winner.neighbors + loser.neighbors) - {winner.name})
    winner.military_strength = min(winner.military_strength, winner.military_cap)
    world.countries.remove(loser)
    print(f"  >> {winner.name} has annexed {loser.name}!")

def get_valid_neighbors(country, world):
    existing_names = {c.name for c in world.countries}
    return [c for c in world.countries if c.name in country.neighbors and c.name in existing_names]

def get_targets(country, world):
    valid = get_valid_neighbors(country, world)
    if valid:
        return valid
    others = [c for c in world.countries if c != country]
    return random.sample(others, min(3, len(others)))

def print_status(world):
    if world.active_conflicts:
        print(f"  Active conflicts ({len(world.active_conflicts)}):")
        for c in world.active_conflicts:
            print(f"    {c.attacker.name} ({int(c.attacker.military_strength):,}) vs {c.defender.name} ({int(c.defender.military_strength):,}) - Day {c.duration_days}")

    if world.current_day % 10 == 0:
        print(f"\n  Top 5 countries by military strength:")
        top = sorted(world.countries, key=lambda c: c.military_strength, reverse=True)[:5]
        for c in top:
            print(f"    {c.name}: {int(c.military_strength):,} troops, economy {int(c.economy):,}")
        print()

def apply_events(world, events):
    non_combat_events = [e for e in events if e.type not in ("invasion", "war")]
    for country in world.countries:
        if random.random() < 0.1:
            event = random.choice(non_combat_events)
            country.economy = max(0, int(country.economy * (1 + event.economy_impact)))
            country.military_strength = max(0, int(country.military_strength * (1 + event.military_impact)))
            country.military_strength = min(country.military_strength, country.military_cap)
            country.population = max(1, int(country.population * (1 + event.population_impact)))
            flavor = random.choice(event.flavor) if event.flavor else ""
            print(f"  [EVENT] {country.name} - {event.name}: {flavor}")

def simulate_day(world, events):
    apply_events(world, events)

    for conflict in list(world.active_conflicts):
        conflict.simulate_day()
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
        attack_chance = base_probability * strength_ratio * world.risk

        if random.random() < attack_chance:
            if strength_ratio >= INVASION_THRESHOLD:
                print(f"  >> {country.name} invades {target.name} and conquers them instantly!")
                annexe(country, target, world)
            else:
                conflict = Conflict(country, target)
                world.active_conflicts.append(conflict)
                print(f"  >> {country.name} declares war on {target.name}!")

def main():
    print("Loading world data...")
    countries = load_countries()
    events = load_events()

    world = World(
        stability=1.0,
        risk=0.15,
        countries=countries
    )

    print(f"World initialized with {len(world.countries)} countries.")
    print(f"Simulation start date: {START_DATE.strftime('%B %d, %Y')}")
    print("Starting simulation...\n")

    running = True
    while running:
        world.current_day += 1
        date_str = current_date(world).strftime("%B %d, %Y")

        simulate_day(world, events)

        print(f"{date_str} - {len(world.countries)} countries remaining")
        print_status(world)

        time.sleep(sleep_time)

        if len(world.countries) <= 1:
            date_str = current_date(world).strftime("%B %d, %Y")
            print(f"\nSimulation over! {world.countries[0].name} conquered the world on {date_str}!")
            print(f"Total simulation time: {world.current_day} days ({world.current_day // 365} years, {world.current_day % 365} days)")
            running = False

if __name__ == "__main__":
    main()