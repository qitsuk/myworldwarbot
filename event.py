import json

class Event:
    def __init__(self, type, name, base_probability, economy_impact, military_impact, population_impact, flavor=None):
        self.type = type
        self.name = name
        self.base_probability = base_probability
        self.economy_impact = economy_impact
        self.military_impact = military_impact
        self.population_impact = population_impact
        self.flavor = flavor or []

    @staticmethod
    def load_events(filepath="events.json"):
        with open(filepath, "r") as f:
            data = json.load(f)
        
        return [
            Event(
                type=event["type"],
                name=event["name"],
                base_probability=event["probability"],
                economy_impact=event["economy_impact"],
                military_impact=event["military_impact"],
                population_impact=event["population_impact"],
                flavor=event.get("flavor", [])
            )
            for event in data["events"]
        ]