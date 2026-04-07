class Country:
    def __init__(self, name, population, population_growth, economy, military_strength, territory, neighbors=None):
        self.name = name
        self.population = population  # Skal sættes FØR military_cap kaldes!
        self.population_growth = population_growth
        self.economy = economy
        self.territory = territory
        self.neighbors = neighbors if neighbors is not None else []
        self.military_strength = min(military_strength, self.military_cap)

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