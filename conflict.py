import random
from logger import log

NUCLEAR_TRIGGER_THRESHOLD = 0.25   # launch when below 25% of strength at conflict start
NUCLEAR_TRIGGER_CHANCE    = 0.06   # 6% per month once desperate

PEACE_THRESHOLD           = 0.35   # loser below 35% of start strength → peace can be offered
PEACE_OFFER_CHANCE        = 0.15   # 15% per tick the winning side proposes terms
LOSER_ACCEPT_CHANCE       = 0.60   # base chance the losing side accepts
MERGER_DEMAND_CHANCE      = 0.40   # chance the loser demands a merger as their condition
WINNER_ACCEPT_MERGER      = 0.50   # chance the winner agrees to a merger
PYRRHIC_RATIO             = 0.55   # fraction of loser's resources winner absorbs after refused peace

CIVILIAN_CASUALTY_RATE    = 0.003  # 0.3% of population lost per side per month of active war

GUERRILLA_THRESHOLD  = 0.20   # guerrillas only emerge once a side has lost 20%+ of start strength
GUERRILLA_RATE       = 0.04   # up to 4% of civilians take up arms at peak desperation
GUERRILLA_EFFICIENCY = 0.22   # guerrillas are ~22% as effective as trained soldiers
                               # (terrain knowledge offsets lack of training/equipment)


class Conflict:
    def __init__(self, attacker, defender):
        self.attacker = attacker
        self.defender = defender
        self.duration_days = 0
        self._attacker_start = max(attacker.military_strength, 1)
        self._defender_start = max(defender.military_strength, 1)

        # Peace negotiation outcome
        # 'annexation' | 'merger' | None (military defeat)
        self.peace_deal   = None
        # True when the winner refused a valid peace offer — pyrrhic conquest penalty applies
        self.pyrrhic      = False
        # Cached winner/loser when peace is struck (military hasn't hit 0 yet)
        self._peace_winner = None
        self._peace_loser  = None

    def _guerrilla_strength(self, side, start_strength):
        """Effective guerrilla contribution for a side that's taking heavy losses.
        Guerrillas are defenders — they fight for their homeland, not to invade.
        They emerge gradually as the regular military is ground down."""
        desperation = max(0.0, 1.0 - side.military_strength / max(start_strength, 1))
        if desperation < GUERRILLA_THRESHOLD:
            return 0
        # Participation scales from 0 → GUERRILLA_RATE as losses go from threshold → 80%
        scale = min(1.0, (desperation - GUERRILLA_THRESHOLD) / (0.80 - GUERRILLA_THRESHOLD))
        civilians = max(0, side.population - side.military_strength)
        return int(civilians * GUERRILLA_RATE * scale * GUERRILLA_EFFICIENCY)

    def simulate_day(self, nation_count=999, endgame_threshold=2):
        self.duration_days += 1

        attacker_roll = random.uniform(0.7, 1.3)
        defender_roll = random.uniform(0.7, 1.3)

        tech_ratio = self.attacker.tech_level / max(self.defender.tech_level, 0.1)

        # Guerrillas supplement the losing side's defensive strength.
        # They're partially tech-resistant (terrain, concealment) so only half the tech
        # penalty applies to them — a guerrilla in the jungle is harder to bomb than a tank.
        attacker_guerrillas = self._guerrilla_strength(self.attacker, self._attacker_start)
        defender_guerrillas = self._guerrilla_strength(self.defender, self._defender_start)
        attacker_effective  = self.attacker.military_strength + attacker_guerrillas * (1 + (tech_ratio - 1) * 0.5)
        defender_effective  = self.defender.military_strength + defender_guerrillas * (1 + (1 / tech_ratio - 1) * 0.5)

        attacker_losses = (defender_effective * 0.08) * attacker_roll * 1.2 / tech_ratio
        defender_losses = (attacker_effective * 0.08) * defender_roll * 0.8 * tech_ratio

        self.attacker.military_strength = max(0, self.attacker.military_strength - attacker_losses)
        self.defender.military_strength = max(0, self.defender.military_strength - defender_losses)

        self.attacker.military_strength = min(self.attacker.military_strength, self.attacker.military_cap)
        self.defender.military_strength = min(self.defender.military_strength, self.defender.military_cap)

        # Civilian casualties — base rate plus extra for guerrilla fighters killed in action
        for side, guerrillas in ((self.attacker, attacker_guerrillas), (self.defender, defender_guerrillas)):
            guerrilla_dead = int(guerrillas * 0.08 * random.uniform(0.7, 1.3))
            pop_loss = int(side.population * CIVILIAN_CASUALTY_RATE) + guerrilla_dead
            side.population = max(1, side.population - pop_loss)

        self._check_nuclear_escalation(nation_count, endgame_threshold)
        if not self.peace_deal:
            self._check_peace_offer()

    def _check_peace_offer(self):
        """Winning side may offer peace once the loser is desperate enough."""
        # Identify current winning / losing side by military strength
        if self.attacker.military_strength >= self.defender.military_strength:
            winning, losing = self.attacker, self.defender
            losing_start = self._defender_start
        else:
            winning, losing = self.defender, self.attacker
            losing_start = self._attacker_start

        # Only when the loser has dropped far enough
        if losing.military_strength > losing_start * PEACE_THRESHOLD:
            return
        if random.random() > PEACE_OFFER_CHANCE:
            return

        log(f"  [PEACE] {winning.name} offers peace terms to {losing.name}.")

        # Loser's roll — desperation increases acceptance
        desperation  = 1.0 - losing.military_strength / max(losing_start, 1)
        accept_chance = min(0.95, LOSER_ACCEPT_CHANCE + desperation * 0.30)

        if random.random() > accept_chance:
            log(f"  [PEACE] {losing.name} refuses — they will fight to the last!")
            return

        # Loser accepted — do they demand a merger?
        if random.random() < MERGER_DEMAND_CHANCE:
            log(f"  [PEACE] {losing.name} will surrender — but only as a union, not a conquest.")
            if random.random() < WINNER_ACCEPT_MERGER:
                log(f"  [PEACE] {winning.name} agrees. A new nation will be born from this war.")
                self.peace_deal   = 'merger'
                self._peace_winner = winning
                self._peace_loser  = losing
            else:
                log(f"  [PEACE] {winning.name} rejects the union. The war continues — but victory will be costly.")
                self.pyrrhic = True   # penalty applied on eventual military defeat
        else:
            log(f"  [PEACE] {losing.name} surrenders unconditionally to {winning.name}.")
            self.peace_deal   = 'annexation'
            self._peace_winner = winning
            self._peace_loser  = losing

    def _check_nuclear_escalation(self, nation_count=999, endgame_threshold=2):
        """A desperate nuclear power may launch a last-resort strike."""
        endgame = nation_count <= endgame_threshold
        chance  = min(0.60, NUCLEAR_TRIGGER_CHANCE * 25) if endgame else NUCLEAR_TRIGGER_CHANCE
        start_map = {self.attacker: self._attacker_start, self.defender: self._defender_start}
        for launcher, target in [(self.attacker, self.defender), (self.defender, self.attacker)]:
            if launcher.nukes <= 0:
                continue
            if not endgame and launcher.military_strength > start_map[launcher] * NUCLEAR_TRIGGER_THRESHOLD:
                continue
            if random.random() > chance:
                continue

            used = min(launcher.nukes, max(1, launcher.nukes // 5))
            launcher.nukes -= used
            launcher.nuked = True

            log(f"  [NUCLEAR] \u2622 {launcher.name} launches {used} nuclear weapon(s) at {target.name}!")

            launcher.military_strength = max(0, launcher.military_strength * 0.50)
            target.military_strength   = max(0, target.military_strength   * 0.25)
            launcher.population = max(1, int(launcher.population * 0.88))
            target.population   = max(1, int(target.population   * 0.72))
            launcher.economy = max(0, int(launcher.economy * 0.65))
            target.economy   = max(0, int(target.economy   * 0.45))

            log(f"  [NUCLEAR] \u2622 Catastrophic damage to both sides! {target.name} loses 75% military, 28% population, 55% economy.")
            break

    @property
    def is_over(self):
        return (self.peace_deal is not None or
                self.attacker.military_strength <= 0 or
                self.defender.military_strength <= 0)

    @property
    def winner(self):
        if self._peace_winner:
            return self._peace_winner
        if self.attacker.military_strength <= 0:
            return self.defender
        if self.defender.military_strength <= 0:
            return self.attacker
        return None

    @property
    def loser(self):
        if self._peace_loser:
            return self._peace_loser
        if self.attacker.military_strength <= 0:
            return self.attacker
        if self.defender.military_strength <= 0:
            return self.defender
        return None

    def __repr__(self):
        return f"Conflict({self.attacker.name} vs {self.defender.name}, day {self.duration_days})"
