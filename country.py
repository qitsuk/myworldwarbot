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