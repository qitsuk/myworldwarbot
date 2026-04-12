import random
from logger import log

_NUCLEAR_LAUNCH_FLAVORS = [
    "{launcher} crosses the nuclear threshold, firing {used} warhead(s) at {target}.",
    "The unthinkable happens: {launcher} launches {used} nuclear weapon(s) at {target}.",
    "Desperate and cornered, {launcher} fires {used} nuclear weapon(s) at {target}.",
    "{launcher} unleashes nuclear devastation on {target}.",
    "The mushroom clouds rise: {launcher} has struck {target} with {used} warhead(s).",
    "A last resort becomes reality — {launcher} launches nuclear strikes on {target}.",
    "With its back against the wall, {launcher} deploys {used} nuclear weapon(s) against {target}.",
    "{launcher} breaks the nuclear taboo, striking {target} with {used} weapon(s).",
    "Nuclear fire rains down on {target} as {launcher} fires {used} warhead(s).",
    "The world watches in horror as {launcher} launches {used} nuclear weapon(s) at {target}.",
]

_PEACE_OFFER_FLAVORS = [
    "{winner} extends an offer of peace to {loser}.",
    "Sensing victory, {winner} offers {loser} a way out.",
    "{winner} reaches out diplomatically — peace terms are on the table for {loser}.",
    "Rather than annihilate, {winner} chooses to negotiate with {loser}.",
    "{winner}'s generals send envoys to {loser} with peace terms.",
    "The war may be ending: {winner} has offered {loser} terms to end the fighting.",
    "A white flag is waved — {winner} and {loser} begin peace talks.",
    "Battlefield dominance gives {winner} the leverage to offer peace to {loser}.",
    "{winner} signals it will accept {loser}'s surrender on favourable terms.",
    "A ceasefire proposal: {winner} offers {loser} terms to end the fighting.",
]

_PEACE_REFUSAL_FLAVORS = [
    "{loser} rejects the offer. The fighting goes on.",
    "No surrender — {loser} vows to fight to the bitter end.",
    "Pride wins over pragmatism: {loser} refuses to yield.",
    "The terms are rejected. {loser} will bleed before it surrenders.",
    "{loser} sends back the envoys empty-handed.",
    "No deal. {loser} would sooner burn than accept {winner}'s terms.",
    "Defiance rules the day — {loser} will not capitulate.",
    "{loser} chooses honour over survival and rejects the peace offer.",
    "The war drags on — {loser} refuses {winner}'s terms.",
    "{loser} spits on {winner}'s peace terms.",
]

_PEACE_MERGER_DEMAND_FLAVORS = [
    "{loser} will lay down its arms — but only as an equal partner, not a subject.",
    "{loser} offers a compromise: union or nothing.",
    "Rather than be conquered, {loser} demands to be absorbed as a full partner.",
    "{loser}'s terms are clear — merge or fight to the last.",
    "Pride and pragmatism clash: {loser} insists on a union, not a surrender.",
    "{loser} will not be erased. It demands unity with {winner}.",
    "A nation fights for its identity — {loser} will accept only a merger.",
    "{loser}'s final offer: become one, or continue the war.",
]

_PEACE_MERGER_ACCEPT_FLAVORS = [
    "{winner} agrees. A new nation will rise from the ashes of this war.",
    "The terms are accepted. Two nations will soon become one.",
    "{winner} sees wisdom in the offer — a union is forged.",
    "Peace through union: {winner} accepts {loser}'s terms.",
    "History is made — {winner} agrees to merge with {loser}.",
    "A new chapter begins as {winner} embraces unity over conquest.",
    "The war ends not with conquest, but with cooperation.",
    "{winner} puts down its sword and extends a hand instead.",
]

_PEACE_MERGER_REJECT_FLAVORS = [
    "{winner} refuses. Conquest, not compromise, will settle this.",
    "The offer is declined. {winner} will not share power.",
    "{winner} wants territory, not a partnership.",
    "No union — {winner} intends to absorb {loser} on its own terms.",
    "Ambition overrules wisdom — {winner} turns down the union offer.",
    "{winner} demands full surrender, nothing less.",
    "The war goes on — {winner} won't settle for a merger.",
    "The pyrrhic road ahead: {winner} rejects the merger and presses on.",
]

_PEACE_SURRENDER_FLAVORS = [
    "{loser} lays down its arms and surrenders to {winner}.",
    "With no options left, {loser} yields unconditionally to {winner}.",
    "{loser}'s leaders sign the instrument of surrender before {winner}.",
    "The white flag flies over {loser} — it submits to {winner}.",
    "Resistance ends as {loser} capitulates to {winner}.",
    "Crushed and exhausted, {loser} surrenders to {winner}.",
    "{loser} accepts defeat. {winner} dictates the terms.",
    "Beaten on all fronts, {loser} offers its unconditional surrender to {winner}.",
    "{loser} concedes. The war is over, and {winner} has won.",
    "The fighting stops — {loser} has surrendered to {winner}.",
]

_PEACE_PYRRHIC_FLAVORS = [
    "{winner} wins, but at terrible cost — the ruins of {loser} are its prize.",
    "Victory belongs to {winner}, but the price was ruinous.",
    "{winner} stands over the wreckage it refused to spare — a hollow triumph.",
    "The war is won, but {winner} inherits little more than ash from {loser}.",
    "They won. They lost. {winner} claims the scorched earth that was {loser}.",
    "{winner} refused peace and paid for it — what remains of {loser} is almost worthless.",
    "A costly conquest: {winner} absorbs what little survives of {loser}.",
    "Pride before profit: {winner} wins the war but loses the peace.",
]

NUCLEAR_TRIGGER_THRESHOLD = 0.25   # start rolling for launch below 25% of starting strength
NUCLEAR_TRIGGER_CHANCE    = 0.08   # 8% per month at the trigger threshold
NUCLEAR_PANIC_CHANCE      = 0.45   # 45% per month when nearly eliminated (≤ 5% of starting strength)

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

        # Nuclear strikes that fired this tick — drained into world.pending_strikes by simulate_day()
        self.pending_strikes = []

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

        flavor = random.choice(_PEACE_OFFER_FLAVORS).format(winner=winning.name, loser=losing.name)
        log(f"  [PEACE] {flavor}")

        # Loser's roll — desperation increases acceptance
        desperation  = 1.0 - losing.military_strength / max(losing_start, 1)
        accept_chance = min(0.95, LOSER_ACCEPT_CHANCE + desperation * 0.30)

        if random.random() > accept_chance:
            flavor = random.choice(_PEACE_REFUSAL_FLAVORS).format(loser=losing.name, winner=winning.name)
            log(f"  [PEACE] {flavor}")
            return

        # Loser accepted — do they demand a merger?
        if random.random() < MERGER_DEMAND_CHANCE:
            flavor = random.choice(_PEACE_MERGER_DEMAND_FLAVORS).format(loser=losing.name, winner=winning.name)
            log(f"  [PEACE] {flavor}")
            if random.random() < WINNER_ACCEPT_MERGER:
                flavor = random.choice(_PEACE_MERGER_ACCEPT_FLAVORS).format(winner=winning.name, loser=losing.name)
                log(f"  [PEACE] {flavor}")
                self.peace_deal   = 'merger'
                self._peace_winner = winning
                self._peace_loser  = losing
            else:
                flavor = random.choice(_PEACE_MERGER_REJECT_FLAVORS).format(winner=winning.name, loser=losing.name)
                log(f"  [PEACE] {flavor}")
                self.pyrrhic = True   # penalty applied on eventual military defeat
        else:
            flavor = random.choice(_PEACE_SURRENDER_FLAVORS).format(loser=losing.name, winner=winning.name)
            log(f"  [PEACE] {flavor}")
            self.peace_deal   = 'annexation'
            self._peace_winner = winning
            self._peace_loser  = losing

    def _check_nuclear_escalation(self, nation_count=999, endgame_threshold=2):
        """A desperate nuclear power may launch a last-resort strike.

        Chance scales smoothly from NUCLEAR_TRIGGER_CHANCE at the trigger threshold
        up to NUCLEAR_PANIC_CHANCE as the launcher nears total elimination.
        Endgame (≤2 nations left) forces the panic rate unconditionally.
        """
        endgame   = nation_count <= endgame_threshold
        start_map = {self.attacker: self._attacker_start, self.defender: self._defender_start}
        for launcher, target in [(self.attacker, self.defender), (self.defender, self.attacker)]:
            if launcher.nukes <= 0:
                continue
            start = max(start_map[launcher], 1)
            strength_ratio = launcher.military_strength / start
            if not endgame and strength_ratio > NUCLEAR_TRIGGER_THRESHOLD:
                continue
            if endgame:
                chance = NUCLEAR_PANIC_CHANCE
            else:
                # Linear gradient: NUCLEAR_TRIGGER_CHANCE at threshold → NUCLEAR_PANIC_CHANCE at 0
                t      = 1.0 - (strength_ratio / NUCLEAR_TRIGGER_THRESHOLD)  # 0 at threshold, 1 at zero
                chance = NUCLEAR_TRIGGER_CHANCE + t * (NUCLEAR_PANIC_CHANCE - NUCLEAR_TRIGGER_CHANCE)
            if random.random() > chance:
                continue

            used = min(launcher.nukes, max(1, launcher.nukes // 5))
            launcher.nukes -= used
            launcher.nuked  = True
            target.was_nuked = True
            self.pending_strikes.append((launcher.name, target.name))

            flavor = random.choice(_NUCLEAR_LAUNCH_FLAVORS).format(launcher=launcher.name, used=used, target=target.name)
            log(f"  [NUCLEAR] \u2622 {flavor}")

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
