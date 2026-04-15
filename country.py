from weapons import WEAPON_KEYS


class Country:
    def __init__(self, name, population, population_growth, economy, military_strength, territory, neighbors=None, color='#888888', nukes=0, tech_level=1.0):
        self.name = name
        self.population = population  # Skal sættes FØR military_cap kaldes!
        self.population_growth = population_growth
        self.economy = economy
        self.territory = territory
        self.neighbors = neighbors if neighbors is not None else []
        self.military_strength = min(military_strength, self.military_cap)
        self.color = color
        self.absorbed_names = [name]  # all original country names this country controls
        self.nukes = nukes            # nuclear warhead count
        self.nuked = False            # True once this nation has launched a nuclear strike
        self.tech_level = tech_level  # military technology multiplier (1.0–3.0)
        self.war_exhaustion = 0.0     # 0–1 modifier reducing willingness to start new wars
        self.uranium = 0.0            # enriched uranium stockpile (units; URANIUM_PER_NUKE → 1 warhead)
        self.was_nuked = False        # True once this nation has received a nuclear strike
        self.cities = []              # list of {"name", "lat", "lon", "pop"} used for nuclear targeting

        # ── Special weapons ──────────────────────────────────────────────
        # Research progress: 0.0 → 1.0 for each weapon key
        self.research = {k: 0.0 for k in WEAPON_KEYS}
        # Consumed stockpiles
        self.drones            = 0
        self.hypersonic        = 0
        self.emp_arsenal       = 0
        self.neutron_bombs     = 0
        self.kinetic_impactors = 0
        self.nano_arsenal      = 0
        self.tectonic_arsenal  = 0
        # Passive levels (0.0 – 1.0)
        self.cyber_level       = 0.0
        self.ai_combat_level   = 0.0
        self.shield_level      = 0.0
        self.orbital_laser_level   = 0.0
        self.orbital_laser_charges = 0
        # Diplomatic / casus belli
        self.casus_belli = set()  # set of country names this country has a casus belli against

    @property
    def military_cap(self):
        adult_population = self.population * 0.75
        return int(adult_population * 0.20)

    @property
    def potential_strength(self):
        return self.economic_growth * self.population * self.population_growth

    @property
    def economic_growth(self):
        return self.population_growth * self.population * self.economy