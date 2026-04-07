import random

class Conflict:
    def __init__(self, attacker, defender):
        self.attacker = attacker
        self.defender = defender
        self.duration_days = 0

    def simulate_day(self):
        self.duration_days += 1

        attacker_roll = random.uniform(0.7, 1.3)
        defender_roll = random.uniform(0.7, 1.3)

        attacker_losses = (self.defender.military_strength * 0.02) * attacker_roll * 1.2
        defender_losses = (self.attacker.military_strength * 0.02) * defender_roll * 0.8

        self.attacker.military_strength = max(0, self.attacker.military_strength - attacker_losses)
        self.defender.military_strength = max(0, self.defender.military_strength - defender_losses)

        self.attacker.military_strength = min(self.attacker.military_strength, self.attacker.military_cap)
        self.defender.military_strength = min(self.defender.military_strength, self.defender.military_cap)

    @property
    def is_over(self):
        return self.attacker.military_strength <= 0 or self.defender.military_strength <= 0

    @property
    def winner(self):
        if self.attacker.military_strength <= 0:
            return self.defender
        if self.defender.military_strength <= 0:
            return self.attacker
        return None

    @property
    def loser(self):
        if self.attacker.military_strength <= 0:
            return self.attacker
        if self.defender.military_strength <= 0:
            return self.defender
        return None

    def __repr__(self):
        return f"Conflict({self.attacker.name} vs {self.defender.name}, day {self.duration_days})"