import json
import math
import random
import colorsys
from country import Country
from event import Event
from cities import CITIES
from weapons import init_country_weapons

# Year the data in countries.json was sourced from
DATA_YEAR = 2024

# Real-world nuclear warhead estimates (approximate)
NUCLEAR_NATIONS = {
    "Russia":         6257,
    "United States":  5500,
    "China":           350,
    "France":          290,
    "United Kingdom":  225,
    "Pakistan":        165,
    "India":           160,
    "Israel":           90,
    "North Korea":      40,
}


def _extrapolate(population, economy, population_growth, years):
    """Project population and economy forward by `years` years.

    GDP growth uses a convergence model — poor countries grow faster than rich ones.
    Population growth uses a log-scale demographic transition: the fertility decline
    that in the real world begins around $3k–$5k/cap is captured by the log ratio,
    so even moderately poor countries see meaningful dampening over long horizons.
    Both effects compound year-by-year.
    """
    for _ in range(years):
        gdp_per_capita = economy / max(population, 1)
        # Convergence GDP growth: $250/cap ≈ 4.6 %, $5k ≈ 2.8 %, $50k ≈ 1.5 %, floor 0.5 %
        gdp_growth = max(0.005, 0.065 - 0.01 * math.log10(max(gdp_per_capita, 100)))
        # Demographic transition: log-scale dampening, floor 5 % of base rate
        # $500/cap ≈ 49 % of base; $2k/cap ≈ 37 %; $10k ≈ 25 %; $50k ≈ 11 %
        gdp_factor    = math.log10(max(gdp_per_capita, 100)) / math.log10(200_000)
        wealth_factor = max(0.05, 1.0 - gdp_factor)
        adj_pop_growth = population_growth * wealth_factor
        population = max(1, int(population * (1 + adj_pop_growth)))
        economy    = int(economy    * (1 + gdp_growth))
    return population, economy


def _make_color(index):
    """Generate a perceptually distinct color using the golden-angle hue distribution."""
    hue = (index * 137.508) % 360
    r, g, b = colorsys.hls_to_rgb(hue / 360, 0.42, 0.65)
    return '#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255))


def _make_tech_level(economy, population):
    """Derive starting tech level from GDP per capita (logarithmic, no hard cap).
    ~1.5 for very poor nations, ~3–4 for middle income, ~5+ for wealthy."""
    gdp_per_capita = economy / max(population, 1)
    return round(1.0 + 2.0 * math.log10(1 + gdp_per_capita / 500), 2)


def load_countries(filepath="countries.json", variance=0.15, start_year=None):
    with open(filepath, "r") as f:
        data = json.load(f)

    years_ahead = max(0, (start_year or DATA_YEAR) - DATA_YEAR)

    # Sort names alphabetically so color assignment is stable across runs
    sorted_names = sorted(c["name"] for c in data["countries"])
    name_to_color = {name: _make_color(i) for i, name in enumerate(sorted_names)}

    countries = []
    for c in data["countries"]:
        def vary(value):
            return value * random.uniform(1 - variance, 1 + variance)

        base_population   = int(vary(c["population"]))
        base_economy      = int(vary(c["economy"]))
        base_military     = int(vary(c["military_strength"]))
        base_pop_growth   = round(vary(c["population_growth"]), 4)

        if years_ahead > 0:
            population, economy = _extrapolate(
                base_population, base_economy, base_pop_growth, years_ahead
            )
            # Scale military with population; capped by Country.military_cap in constructor
            military = int(base_military * (population / max(base_population, 1)))
            # Adjust stored growth rate to reflect end-state wealth level
            final_gdp_pc  = economy / max(population, 1)
            gdp_factor    = math.log10(max(final_gdp_pc, 100)) / math.log10(200_000)
            wealth_factor = max(0.05, 1.0 - gdp_factor)
            population_growth = round(base_pop_growth * wealth_factor, 4)
        else:
            population, economy, military = base_population, base_economy, base_military
            population_growth = base_pop_growth

        country = Country(
            name=c["name"],
            population=population,
            population_growth=population_growth,
            economy=economy,
            military_strength=military,
            territory=c["territory"],
            neighbors=c.get("neighbors", []),
            color=name_to_color[c["name"]],
            nukes=NUCLEAR_NATIONS.get(c["name"], 0),
            tech_level=_make_tech_level(economy, population),
        )
        country.cities = CITIES.get(c["name"], [])
        init_country_weapons(country, start_year or DATA_YEAR)
        countries.append(country)

    return countries


def load_events(filepath="events.json"):
    return Event.load_events(filepath)
