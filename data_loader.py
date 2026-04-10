import json
import math
import random
import colorsys
from country import Country
from event import Event

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


def load_countries(filepath="countries.json", variance=0.15):
    with open(filepath, "r") as f:
        data = json.load(f)

    # Sort names alphabetically so color assignment is stable across runs
    sorted_names = sorted(c["name"] for c in data["countries"])
    name_to_color = {name: _make_color(i) for i, name in enumerate(sorted_names)}

    countries = []
    for c in data["countries"]:
        def vary(value):
            return value * random.uniform(1 - variance, 1 + variance)

        economy    = int(vary(c["economy"]))
        population = int(vary(c["population"]))

        country = Country(
            name=c["name"],
            population=population,
            population_growth=round(vary(c["population_growth"]), 4),
            economy=economy,
            military_strength=int(vary(c["military_strength"])),
            territory=c["territory"],
            neighbors=c.get("neighbors", []),
            color=name_to_color[c["name"]],
            nukes=NUCLEAR_NATIONS.get(c["name"], 0),
            tech_level=_make_tech_level(economy, population),
        )
        countries.append(country)

    return countries


def load_events(filepath="events.json"):
    return Event.load_events(filepath)
