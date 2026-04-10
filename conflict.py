import random
from logger import log

NUCLEAR_TRIGGER_THRESHOLD = 0.25   # launch when below 25% of strength at conflict start
NUCLEAR_TRIGGER_CHANCE    = 0.06   # 6% per month once desperate


class Conflict:
    def __init__(self, attacker, defender):
        self.attacker = attacker
        self.defender = defender
        self.duration_days = 0
        # Snapshot strengths at conflict start — nuclear trigger is relative to these,
        # not military_cap (which can be far larger than actual deployed forces)
        self._attacker_start = max(attacker.military_strength, 1)
        self._defender_start = max(defender.military_strength, 1)

    def simulate_day(self, nation_count=999, endgame_threshold=2):
        self.duration_days += 1

        attacker_roll = random.uniform(0.7, 1.3)
        defender_roll = random.uniform(0.7, 1.3)

        # Tech advantage: better technology means fewer own losses, more enemy losses
        tech_ratio = self.attacker.tech_level / max(self.defender.tech_level, 0.1)

        # 0.08 per tick — scaled for monthly ticks (≈ 1–2 year wars between equal powers)
        attacker_losses = (self.defender.military_strength * 0.08) * attacker_roll * 1.2 / tech_ratio
        defender_losses = (self.attacker.military_strength * 0.08) * defender_roll * 0.8 * tech_ratio

        self.attacker.military_strength = max(0, self.attacker.military_strength - attacker_losses)
        self.defender.military_strength = max(0, self.defender.military_strength - defender_losses)

        self.attacker.military_strength = min(self.attacker.military_strength, self.attacker.military_cap)
        self.defender.military_strength = min(self.defender.military_strength, self.defender.military_cap)

        self._check_nuclear_escalation(nation_count, endgame_threshold)

    def _check_nuclear_escalation(self, nation_count=999, endgame_threshold=2):
        """A desperate nuclear power may launch a last-resort strike."""
        endgame = nation_count <= endgame_threshold
        chance = min(0.60, NUCLEAR_TRIGGER_CHANCE * 25) if endgame else NUCLEAR_TRIGGER_CHANCE
        start_map = {self.attacker: self._attacker_start, self.defender: self._defender_start}
        for launcher, target in [(self.attacker, self.defender), (self.defender, self.attacker)]:
            if launcher.nukes <= 0:
                continue
            # Must have lost at least 80% of the strength they entered this conflict with
            # (gate is bypassed in endgame — nations grow desperate)
            if not endgame and launcher.military_strength > start_map[launcher] * NUCLEAR_TRIGGER_THRESHOLD:
                continue
            if random.random() > chance:
                continue

            used = min(launcher.nukes, max(1, launcher.nukes // 5))
            launcher.nukes -= used
            launcher.nuked = True

            log(f"  [NUCLEAR] \u2622 {launcher.name} launches {used} nuclear weapon(s) at {target.name}!")

            # Devastating — but mutual — consequences
            launcher.military_strength = max(0, launcher.military_strength * 0.50)
            target.military_strength   = max(0, target.military_strength   * 0.25)
            launcher.population = max(1, int(launcher.population * 0.88))
            target.population   = max(1, int(target.population   * 0.72))
            launcher.economy = max(0, int(launcher.economy * 0.65))
            target.economy   = max(0, int(target.economy   * 0.45))

            log(f"  [NUCLEAR] \u2622 Catastrophic damage to both sides! {target.name} loses 75% military, 28% population, 55% economy.")
            break  # one strike per tick max

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
