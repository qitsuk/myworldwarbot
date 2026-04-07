import json
import random
from country import Country
from event import Event

def load_countries(filepath="countries.json", variance=0.15):
    with open(filepath, "r") as f:
        data = json.load(f)
    
    countries = []
    for c in data["countries"]:
        def vary(value):
            return value * random.uniform(1 - variance, 1 + variance)
        
        country = Country(
            name=c["name"],
            population=int(vary(c["population"])),
            population_growth=round(vary(c["population_growth"]), 4),
            economy=int(vary(c["economy"])),
            military_strength=int(vary(c["military_strength"])),
            territory=c["territory"],
            neighbors=c.get("neighbors", [])
        )
        countries.append(country)
    
    return countries

def load_events(filepath="events.json"):
    return Event.load_events(filepath)