import math
import random
from logger import log
from cities import pick_target_city, blast_radius_km, haversine_km, LETHAL_MORTALITY, DAMAGE_MORTALITY, fallout_duration_months
from weapons import WEAPON_KEYS

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

_SURRENDER_OFFER_FLAVORS = [
    "{loser} raises the white flag, requesting terms from {winner}.",
    "Beaten on the battlefield, {loser} seeks a negotiated end to the war.",
    "{loser}'s government signals it is ready to discuss surrender terms with {winner}.",
    "With losses mounting, {loser} reaches out to {winner} for a ceasefire.",
    "A messenger carries {loser}'s request for terms to {winner}.",
    "Facing annihilation, {loser} bids for a negotiated peace with {winner}.",
    "The guns fall quiet briefly — {loser} has asked {winner} for talks.",
    "{loser}'s generals authorise surrender negotiations with {winner}.",
]

_WINNER_ACCEPTS_ANNEXATION_FLAVORS = [
    "{winner} accepts the surrender. {loser} will be absorbed on {winner}'s terms.",
    "Generous in victory, {winner} agrees — {loser} will lay down its arms completely.",
    "{winner} sees an easy conclusion: full absorption of {loser}.",
    "The white flag is recognised. {loser} surrenders unconditionally to {winner}.",
    "No further bloodshed needed — {winner} accepts {loser}'s total capitulation.",
]

_WINNER_ACCEPTS_CEASEFIRE_FLAVORS = [
    "{winner} is satisfied with its gains — {loser} survives, diminished but intact.",
    "Pragmatic victory: {winner} accepts tribute from {loser} rather than prolonged conquest.",
    "{winner} secures concessions from {loser} without the cost of total war.",
    "A punishing peace: {loser} cedes resources to {winner} in exchange for its survival.",
    "{winner} takes what is offered. {loser} pays reparations and lives to rebuild.",
    "The war ends on {winner}'s terms — {loser} pays a heavy toll but keeps its sovereignty.",
    "{winner} accepts a ceasefire. {loser} endures, poorer and humbled.",
]

_WINNER_REJECTS_SURRENDER_FLAVORS = [
    "{winner} rejects the offer. Only total victory will do.",
    "No quarter — {winner} demands unconditional conquest, not negotiation.",
    "{winner} turns away the envoys. The fighting continues.",
    "There will be no ceasefire. {winner} presses on until {loser} is destroyed.",
    "{winner} has come too far to settle for less than everything.",
    "The war goes on — {winner} refuses to let {loser} surrender on its own terms.",
    "{winner} smells blood and refuses to stop short of annihilation.",
]

_NUCLEAR_THREAT_FLAVORS = [
    "{loser} issues a stark warning: accept a ceasefire or face nuclear retaliation.",
    "As a last resort, {loser} threatens to deploy nuclear weapons unless {winner} stands down.",
    "{loser}'s nuclear arsenal casts a long shadow — they warn {winner} to halt the advance.",
    "The spectre of nuclear war: {loser} threatens to use the bomb if {winner} does not stop.",
    "{loser} puts its missiles on alert — a desperate nuclear deterrent against {winner}.",
    "A chilling ultimatum from {loser}: cease hostilities or face nuclear fire.",
]

_NUCLEAR_THREAT_ACCEPTED_FLAVORS = [
    "{winner} halts its advance — {loser}'s nuclear threat has forced a ceasefire.",
    "Staring into the nuclear abyss, {winner} agrees to end hostilities with {loser}.",
    "The bomb wins the peace: {winner} accepts terms rather than risk nuclear annihilation.",
    "{winner}'s generals advise caution — the ceasefire with {loser} is accepted.",
    "Mutually assured destruction speaks louder than any army: {winner} backs down.",
]

_NUCLEAR_THREAT_REJECTED_FLAVORS = [
    "{winner} calls {loser}'s bluff and presses the attack.",
    "Undeterred by the nuclear threat, {winner} refuses to stand down.",
    "{winner}'s resolve holds — the nuclear gambit fails to stop the advance.",
    "{loser}'s threat rings hollow — {winner} continues its campaign.",
    "{winner} dares {loser} to pull the trigger. The advance continues.",
]

TERRITORY_CAPTURE_ATTACKER_COST = 0.12

NUCLEAR_TRIGGER_THRESHOLD = 0.25
NUCLEAR_TRIGGER_CHANCE    = 0.08
NUCLEAR_PANIC_CHANCE      = 0.45

PEACE_THRESHOLD           = 0.50   # loser below 50% of start strength → winner may offer peace
PEACE_OFFER_CHANCE        = 0.25   # 25% per tick the winning side proposes terms
PEACE_OFFER_ENDGAME_MIN   = 0.10
LOSER_ACCEPT_CHANCE       = 0.72   # raised from 0.60 — losing nations are more willing to deal
MERGER_DEMAND_CHANCE      = 0.40
WINNER_ACCEPT_MERGER      = 0.50
PYRRHIC_RATIO             = 0.55

SURRENDER_THRESHOLD       = 0.65   # loser below 65% of start strength may raise white flag
SURRENDER_CHANCE          = 0.15   # raised from 0.09
WINNER_ACCEPT_SURRENDER   = 0.65   # raised from 0.55
WINNER_CEASEFIRE_CHANCE   = 0.60   # raised from 0.50

NUCLEAR_COERCE_THRESHOLD  = 0.35
NUCLEAR_COERCE_CHANCE     = 0.10
WINNER_BACKS_DOWN_BASE    = 0.50

CIVILIAN_CASUALTY_RATE    = 0.003

GUERRILLA_THRESHOLD  = 0.20
GUERRILLA_RATE       = 0.04
GUERRILLA_EFFICIENCY = 0.22

MIN_WAR_DURATION = 3.0  # wars last at least 3 months regardless of military size

NUKE_SPREAD_THRESHOLD = 5  # fire this many or more warheads → spread across multiple cities


_TERRITORY_CAPTURE_FLAVORS = [
    "{attacker} seizes {territory} from {defender} — the front line advances.",
    "After fierce fighting, {attacker} plants its flag in {territory}. {defender} falls back.",
    "The banner of {attacker} flies over {territory}. {defender} regroups.",
    "{territory} falls to {attacker}'s relentless advance. {defender} loses ground.",
    "A strategic breakthrough: {attacker} occupies {territory}, pushing deeper into {defender}.",
    "Wave after wave of troops — {attacker} finally secures {territory} from {defender}.",
    "{defender} cedes {territory} to {attacker} under the weight of defeat.",
    "The conquest continues — {territory} is now under {attacker} control.",
    "{attacker} forces overrun {territory}. {defender}'s territory shrinks.",
    "Despite fierce resistance, {territory} is taken by {attacker}.",
    "{attacker} consolidates control over {territory} as {defender} retreats.",
    "Another piece of {defender} falls — {territory} is now {attacker} land.",
]

_TERRITORY_LAST_STAND_FLAVORS = [
    "{defender} has lost everything but {territory} — a last stand begins.",
    "With all other territory gone, {defender} fights desperately for their homeland {territory}.",
    "{attacker} closes in on {territory} — all that remains of {defender}.",
    "The end approaches for {defender}. {attacker} marches on the capital.",
    "{defender} makes a final stand on home soil. {territory} is all that remains.",
    "Cornered and diminished, {defender} rallies everything for one last defence of {territory}.",
]


class Conflict:
    def __init__(self, attacker, defender):
        self.attacker = attacker
        self.defender = defender
        self.duration_days = 0

        self.contested_territory = defender.absorbed_names[-1]

        n = len(defender.absorbed_names)
        self._defender_garrison = defender.military_strength / max(n, 1)

        self._attacker_start = max(attacker.military_strength, 1)
        self._defender_start = max(self._defender_garrison, 1)

        self.pending_strikes = []

        self.peace_deal   = None
        self.pyrrhic      = False
        self._peace_winner = None
        self._peace_loser  = None

    def _guerrilla_strength(self, side, current_strength, start_strength):
        desperation = max(0.0, 1.0 - current_strength / max(start_strength, 1))
        if desperation < GUERRILLA_THRESHOLD:
            return 0
        scale = min(1.0, (desperation - GUERRILLA_THRESHOLD) / (0.80 - GUERRILLA_THRESHOLD))
        civilians = max(0, side.population - side.military_strength)
        return int(civilians * GUERRILLA_RATE * scale * GUERRILLA_EFFICIENCY)

    def simulate_day(self, nation_count=999, endgame_threshold=2, world=None, scale=1.0):
        self.duration_days += scale

        attacker_roll = random.uniform(0.7, 1.3)
        defender_roll = random.uniform(0.7, 1.3)

        tech_ratio = self.attacker.tech_level / max(self.defender.tech_level, 0.1)

        attacker_str = self.attacker.military_strength
        defender_str = self._defender_garrison

        attacker_guerrillas = self._guerrilla_strength(self.attacker, attacker_str,    self._attacker_start)
        defender_guerrillas = self._guerrilla_strength(self.defender, defender_str,    self._defender_start)
        attacker_effective  = attacker_str + attacker_guerrillas * (1 + (tech_ratio - 1) * 0.5)
        defender_effective  = defender_str + defender_guerrillas * (1 + (1 / tech_ratio - 1) * 0.5)

        attacker_losses = (defender_effective * 0.08) * attacker_roll * 1.2 / tech_ratio * scale
        defender_losses = (attacker_effective * 0.08) * defender_roll * 0.8 * tech_ratio * scale

        attacker_mil_before = self.attacker.military_strength
        self.attacker.military_strength = max(0, self.attacker.military_strength - attacker_losses)
        self.attacker.military_strength = min(self.attacker.military_strength, self.attacker.military_cap)
        attacker_mil_lost = max(0, attacker_mil_before - self.attacker.military_strength)

        garrison_before = self._defender_garrison
        self._defender_garrison = max(0.0, self._defender_garrison - defender_losses)
        actual_garrison_loss = garrison_before - self._defender_garrison
        self.defender.military_strength = max(0.0, self.defender.military_strength - actual_garrison_loss)

        if world is not None:
            world.total_military_casualties += int(attacker_mil_lost + actual_garrison_loss)

        total_civ_lost = 0
        for side, guerrillas in ((self.attacker, attacker_guerrillas), (self.defender, defender_guerrillas)):
            guerrilla_dead = int(guerrillas * 0.08 * random.uniform(0.7, 1.3) * scale)
            pop_loss = int(side.population * CIVILIAN_CASUALTY_RATE * scale) + guerrilla_dead
            side.population = max(1, side.population - pop_loss)
            total_civ_lost += pop_loss
        if world is not None:
            world.total_civilian_casualties += total_civ_lost

        # ── Orbital Kinetic Impactor ──────────────────────────────────────
        if self.attacker.kinetic_impactors > 0 and random.random() < 0.08 * scale:
            self.attacker.kinetic_impactors -= 1
            mil_loss = self.defender.military_strength * 0.25
            self.defender.military_strength = max(0, self.defender.military_strength - mil_loss)
            self._defender_garrison = max(0.0, self._defender_garrison - mil_loss)
            log(f"  [ORBITAL] \u2B07 {self.attacker.name} drops a kinetic impactor on {self.defender.name}.")
            self.pending_strikes.append((self.attacker.name, self.defender.name, None, None, None, 0))

        # ── Orbital Laser Platform ────────────────────────────────────────
        if self.attacker.orbital_laser_charges > 0 and random.random() < 0.30 * scale:
            self.attacker.orbital_laser_charges -= 1
            mil_loss = self._defender_garrison * 0.18
            self._defender_garrison = max(0.0, self._defender_garrison - mil_loss)
            self.defender.military_strength = max(0.0, self.defender.military_strength - mil_loss)
            log(f"  [ORBITAL] \u26A1 {self.attacker.name}'s orbital laser platform strikes {self.defender.name}.")

        # ── Tectonic Weapons ──────────────────────────────────────────────
        if self.attacker.tectonic_arsenal > 0 and random.random() < 0.03 * scale:
            self.attacker.tectonic_arsenal -= 1
            log(f"  [TECTONIC] \U0001F30D {self.attacker.name} activates tectonic weapons! The ground tears apart under {self.defender.name}.")
            self.defender.economy = max(1, int(self.defender.economy * 0.3))
            self.defender.population = max(1, int(self.defender.population * 0.7))
            self.defender.military_strength = max(0, self.defender.military_strength * 0.4)
            self._defender_garrison = max(0.0, self._defender_garrison * 0.4)
            if world is not None:
                for neighbor_name in self.defender.absorbed_names + list(getattr(self.defender, 'neighbors', [])):
                    for nc in world.countries:
                        if nc is self.defender or nc is self.attacker:
                            continue
                        if neighbor_name in nc.absorbed_names or nc.name == neighbor_name:
                            nc.economy = max(1, int(nc.economy * 0.85))
                            nc.population = max(1, int(nc.population * 0.92))
                            log(f"  [TECTONIC] \U0001F30D Collateral: {nc.name} struck by seismic shockwaves.")
                            break

        self._check_nuclear_escalation(nation_count, endgame_threshold, world, scale)
        self._check_neutron_escalation(world, scale)
        if not self.peace_deal:
            self._check_peace_offer(scale, nation_count)
        if not self.peace_deal:
            self._check_loser_surrender(scale, nation_count)
        if not self.peace_deal:
            self._check_nuclear_coercion(scale, nation_count, world)

        if (not self.peace_deal
                and self.attacker.military_strength > 0
                and self._defender_garrison <= 0
                and len(self.defender.absorbed_names) > 1):
            self._capture_territory()

    def _endgame_factor(self, nation_count):
        return min(1.0, max(0.0, (nation_count - 2) / 48.0))

    def _check_peace_offer(self, scale=1.0, nation_count=999):
        # No negotiations in the first 3 months — wars must run their course
        if self.duration_days < MIN_WAR_DURATION:
            return

        attacker_str = self.attacker.military_strength
        defender_str = self._defender_garrison

        if attacker_str >= defender_str:
            winning, losing = self.attacker, self.defender
            losing_strength = defender_str
            losing_start    = self._defender_start
        else:
            winning, losing = self.defender, self.attacker
            losing_strength = attacker_str
            losing_start    = self._attacker_start

        if losing_strength > losing_start * PEACE_THRESHOLD:
            return

        ef = self._endgame_factor(nation_count)
        effective_chance = PEACE_OFFER_CHANCE * (PEACE_OFFER_ENDGAME_MIN + (1.0 - PEACE_OFFER_ENDGAME_MIN) * ef)
        if random.random() > effective_chance * scale:
            return

        flavor = random.choice(_PEACE_OFFER_FLAVORS).format(winner=winning.name, loser=losing.name)
        log(f"  [PEACE] {flavor}")

        desperation   = 1.0 - losing_strength / max(losing_start, 1)
        accept_chance = min(0.95, LOSER_ACCEPT_CHANCE + desperation * 0.30)

        if random.random() > accept_chance:
            flavor = random.choice(_PEACE_REFUSAL_FLAVORS).format(loser=losing.name, winner=winning.name)
            log(f"  [PEACE] {flavor}")
            return

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
                self.pyrrhic = True
        else:
            flavor = random.choice(_PEACE_SURRENDER_FLAVORS).format(loser=losing.name, winner=winning.name)
            log(f"  [PEACE] {flavor}")
            self.peace_deal   = 'annexation'
            self._peace_winner = winning
            self._peace_loser  = losing

    def _check_loser_surrender(self, scale=1.0, nation_count=999):
        if self.duration_days < MIN_WAR_DURATION:
            return

        ef = self._endgame_factor(nation_count)
        if ef == 0.0:
            return

        attacker_str = self.attacker.military_strength
        defender_str = self._defender_garrison

        if attacker_str >= defender_str:
            winning, losing = self.attacker, self.defender
            losing_strength = defender_str
            losing_start    = self._defender_start
        else:
            winning, losing = self.defender, self.attacker
            losing_strength = attacker_str
            losing_start    = self._attacker_start

        if losing_strength > losing_start * SURRENDER_THRESHOLD:
            return

        desperation = 1.0 - losing_strength / max(losing_start, 1)
        if random.random() > SURRENDER_CHANCE * ef * (0.5 + desperation) * scale:
            return

        flavor = random.choice(_SURRENDER_OFFER_FLAVORS).format(loser=losing.name, winner=winning.name)
        log(f"  [PEACE] {flavor}")

        accept_chance = WINNER_ACCEPT_SURRENDER * (0.3 + 0.7 * ef)
        if random.random() > accept_chance:
            flavor = random.choice(_WINNER_REJECTS_SURRENDER_FLAVORS).format(winner=winning.name, loser=losing.name)
            log(f"  [PEACE] {flavor}")
            self.pyrrhic = True
            return

        if random.random() < WINNER_CEASEFIRE_CHANCE:
            flavor = random.choice(_WINNER_ACCEPTS_CEASEFIRE_FLAVORS).format(winner=winning.name, loser=losing.name)
            log(f"  [PEACE] {flavor}")
            self.peace_deal    = 'ceasefire'
            self._peace_winner = winning
            self._peace_loser  = losing
        else:
            flavor = random.choice(_WINNER_ACCEPTS_ANNEXATION_FLAVORS).format(winner=winning.name, loser=losing.name)
            log(f"  [PEACE] {flavor}")
            self.peace_deal    = 'annexation'
            self._peace_winner = winning
            self._peace_loser  = losing

    def _check_nuclear_coercion(self, scale=1.0, nation_count=999, world=None):
        if self.duration_days < MIN_WAR_DURATION:
            return

        attacker_str = self.attacker.military_strength
        defender_str = self._defender_garrison

        if attacker_str >= defender_str:
            winning, losing = self.attacker, self.defender
            losing_strength = defender_str
            losing_start    = self._defender_start
        else:
            winning, losing = self.defender, self.attacker
            losing_strength = attacker_str
            losing_start    = self._attacker_start

        if losing.nukes <= 0:
            return
        if losing_strength > losing_start * NUCLEAR_COERCE_THRESHOLD:
            return

        ef = self._endgame_factor(nation_count)
        effective_chance = NUCLEAR_COERCE_CHANCE * max(0.30, ef)
        if random.random() > effective_chance * scale:
            return

        flavor = random.choice(_NUCLEAR_THREAT_FLAVORS).format(loser=losing.name, winner=winning.name)
        log(f"  [PEACE] {flavor}")

        back_down_chance = WINNER_BACKS_DOWN_BASE * (0.25 + 0.75 * ef)
        if random.random() < back_down_chance:
            flavor = random.choice(_NUCLEAR_THREAT_ACCEPTED_FLAVORS).format(winner=winning.name, loser=losing.name)
            log(f"  [PEACE] {flavor}")
            self.peace_deal    = 'ceasefire'
            self._peace_winner = winning
            self._peace_loser  = losing
        else:
            flavor = random.choice(_NUCLEAR_THREAT_REJECTED_FLAVORS).format(winner=winning.name, loser=losing.name)
            log(f"  [PEACE] {flavor}")
            used = min(losing.nukes, max(1, losing.nukes // 4))
            losing.nukes -= used
            self._execute_nuclear_strike(losing, winning, used, world)

    # ── Nuclear strike helpers ────────────────────────────────────────────────

    def _distribute_warheads(self, target, used):
        """Return list of (city, warheads) pairs for this strike.

        When firing fewer than NUKE_SPREAD_THRESHOLD warheads, pick a single city.
        For larger salvos, spread warheads across multiple cities weighted by population.
        """
        cities = getattr(target, 'cities', [])
        if not cities or used < NUKE_SPREAD_THRESHOLD:
            city = pick_target_city(target)
            return [(city, used)]

        # 1 city per 3 warheads, min 2, max min(10, len(cities))
        n_targets = min(len(cities), max(2, used // 3), 10)

        # Weighted sampling without replacement by city population
        remaining = list(cities)
        chosen = []
        for _ in range(n_targets):
            if not remaining:
                break
            weights = [c['pop'] for c in remaining]
            total_w = sum(weights)
            if total_w <= 0:
                chosen.append(remaining.pop(0))
                continue
            r = random.uniform(0, total_w)
            cum = 0.0
            for i, city in enumerate(remaining):
                cum += city['pop']
                if r <= cum:
                    chosen.append(city)
                    remaining.pop(i)
                    break
            else:
                chosen.append(remaining.pop(-1))

        if not chosen:
            return [(pick_target_city(target), used)]

        # Distribute warheads proportional to city population
        total_pop = sum(c['pop'] for c in chosen)
        result = []
        allocated = 0
        for i, city in enumerate(chosen[:-1]):
            n = max(1, round(used * city['pop'] / max(total_pop, 0.001)))
            max_n = used - allocated - (len(chosen) - 1 - i)
            n = min(n, max(1, max_n))
            result.append((city, n))
            allocated += n
        result.append((chosen[-1], max(1, used - allocated)))
        return result

    def _city_damage_fracs(self, target, city, warheads_here):
        """Return (mil_frac, pop_frac, econ_frac, severity_frac) for a single city strike."""
        def sat(density, cap, scale):
            return cap * (1.0 - math.exp(-density / scale))

        if city:
            city_pop_M   = max(city.get('pop', 0.1), 0.01)
            density      = warheads_here / city_pop_M

            city_pop_frac  = sat(density, 0.90, 1.0)
            city_mil_frac  = sat(density, 0.95, 0.8)
            city_econ_frac = sat(density, 0.95, 0.8)

            city_share_pop  = min(1.0, city_pop_M * 1_000_000 / max(target.population, 1))
            city_share_mil  = min(1.0, city_share_pop * 3.0)
            city_share_econ = min(1.0, city_share_pop * 2.5)

            mil_frac  = city_mil_frac  * city_share_mil
            pop_frac  = city_pop_frac  * city_share_pop
            econ_frac = city_econ_frac * city_share_econ
            sev_frac  = city_pop_frac
        else:
            nation_pop_M   = max(target.population / 1_000_000, 0.01)
            density        = warheads_here / nation_pop_M
            mil_frac  = sat(density, 0.92, 2.0)
            pop_frac  = sat(density, 0.55, 2.5)
            econ_frac = sat(density, 0.88, 3.0)
            sev_frac  = mil_frac

        return mil_frac, pop_frac, econ_frac, sev_frac

    def _check_collateral(self, launcher, target, city, warheads_here, world):
        """Check for collateral damage to bystanders from a single city strike."""
        lethal_km, damage_km = blast_radius_km(warheads_here)
        for bystander in list(world.countries):
            if bystander is launcher or bystander is target:
                continue
            for bcity in bystander.cities:
                dist = haversine_km(city['lat'], city['lon'], bcity['lat'], bcity['lon'])
                if dist <= lethal_km:
                    mortality = LETHAL_MORTALITY
                elif dist <= damage_km:
                    mortality = DAMAGE_MORTALITY * (1.0 - (dist - lethal_km) / (damage_km - lethal_km))
                else:
                    continue
                casualties = int(bcity['pop'] * 1_000_000 * mortality)
                if casualties < 1000:
                    continue
                bystander.population = max(1, bystander.population - casualties)
                bystander.was_nuked = True
                world.total_civilian_casualties += casualties
                world.pending_collateral.append(
                    (bystander.name, launcher.name, bcity['name'],
                     casualties, bcity['lat'], bcity['lon'], warheads_here)
                )
                log(f"  [NUCLEAR] \u2622 Collateral: {bcity['name']} ({bystander.name}) struck by fallout — "
                    f"{casualties:,} casualties ({dist:.0f} km from {city['name']})")

    def _execute_nuclear_strike(self, launcher, target, used, world):
        """Apply a nuclear salvo: spread warheads across cities if firing many."""
        launcher.nuked   = True
        target.was_nuked = True
        if world is not None:
            world.total_nukes_used += used

        city_assignments = self._distribute_warheads(target, used)

        # Build log line
        city_names = [c['name'] for c, _ in city_assignments if c]
        if len(city_names) > 1:
            shown = city_names[:4]
            suffix = '…' if len(city_names) > 4 else ''
            city_str = f" ({', '.join(shown)}{suffix})"
        elif city_names:
            city_str = f" ({city_names[0]})"
        else:
            city_str = ""

        n_cities = len(city_assignments)
        spread_note = f", {n_cities} cities" if n_cities > 1 else ""
        flavor = random.choice(_NUCLEAR_LAUNCH_FLAVORS).format(
            launcher=launcher.name, used=used, target=target.name)
        log(f"  [NUCLEAR] \u2622 {flavor}{city_str}")

        # Accumulate damage across city strikes (compound fractions)
        total_mil_frac  = 0.0
        total_pop_frac  = 0.0
        total_econ_frac = 0.0
        worst_sev_frac  = 0.0

        for city, city_warheads in city_assignments:
            mil_f, pop_f, econ_f, sev_f = self._city_damage_fracs(target, city, city_warheads)
            total_mil_frac  = 1.0 - (1.0 - total_mil_frac)  * (1.0 - mil_f)
            total_pop_frac  = 1.0 - (1.0 - total_pop_frac)  * (1.0 - pop_f)
            total_econ_frac = 1.0 - (1.0 - total_econ_frac) * (1.0 - econ_f)
            worst_sev_frac  = max(worst_sev_frac, sev_f)

            if city:
                self.pending_strikes.append((launcher.name, target.name, city['name'], city['lat'], city['lon'], city_warheads))
                if world is not None:
                    self._check_collateral(launcher, target, city, city_warheads, world)
            else:
                self.pending_strikes.append((launcher.name, target.name, None, None, None, city_warheads))

        # Missile shield: intercepts a fraction of incoming warheads
        # Max interception 85% — no shield is perfect against a mass salvo
        shield = getattr(target, 'missile_shield', 0.0)
        if shield > 0:
            intercept = min(0.85, shield * 0.85)
            total_mil_frac  *= (1.0 - intercept)
            total_pop_frac  *= (1.0 - intercept)
            total_econ_frac *= (1.0 - intercept)
            if intercept >= 0.15:
                log(f"  [SHIELD] \U0001F6E1 {target.name}'s missile defence intercepts {intercept*100:.0f}% of incoming warheads.")

        # Apply total damage
        mil_before  = target.military_strength
        pop_before  = target.population
        econ_before = target.economy

        target.military_strength = max(0, target.military_strength * (1.0 - total_mil_frac))
        target.population        = max(1, int(target.population    * (1.0 - total_pop_frac)))
        target.economy           = max(0, int(target.economy       * (1.0 - total_econ_frac)))

        mil_lost  = int(mil_before  - target.military_strength)
        pop_lost  = pop_before  - target.population
        econ_lost = econ_before - target.economy

        if world is not None:
            world.total_military_casualties += mil_lost
            world.total_civilian_casualties += pop_lost

        if worst_sev_frac < 0.15:   severity = "Limited"
        elif worst_sev_frac < 0.40: severity = "Significant"
        elif worst_sev_frac < 0.65: severity = "Severe"
        elif worst_sev_frac < 0.82: severity = "Devastating"
        else:                       severity = "Apocalyptic"

        log(f"  [NUCLEAR] \u2622 {severity} strike ({used} warheads{spread_note}) on {target.name} — "
            f"{mil_lost:,} troops, {pop_lost:,} civilians, \u20ac{econ_lost:,} economy lost.")

    def trigger_opening_strike(self, world):
        """Nuclear first strike fired the moment war is declared."""
        if self.attacker.nukes <= 0:
            return
        used = min(self.attacker.nukes, max(1, self.attacker.nukes // 3))
        self.attacker.nukes -= used
        self._execute_nuclear_strike(self.attacker, self.defender, used, world)

    def _check_nuclear_escalation(self, nation_count=999, endgame_threshold=2, world=None, scale=1.0):
        """A desperate nuclear power may launch a last-resort strike during combat."""
        endgame = nation_count <= endgame_threshold
        strength_map = {self.attacker: self.attacker.military_strength,
                        self.defender: self._defender_garrison}
        start_map    = {self.attacker: self._attacker_start,
                        self.defender: self._defender_start}
        for launcher, target in [(self.attacker, self.defender), (self.defender, self.attacker)]:
            if launcher.nukes <= 0:
                continue
            start = max(start_map[launcher], 1)
            strength_ratio = strength_map[launcher] / start
            if not endgame and strength_ratio > NUCLEAR_TRIGGER_THRESHOLD:
                continue
            if endgame:
                chance = NUCLEAR_PANIC_CHANCE
            else:
                t      = 1.0 - (strength_ratio / NUCLEAR_TRIGGER_THRESHOLD)
                chance = NUCLEAR_TRIGGER_CHANCE + t * (NUCLEAR_PANIC_CHANCE - NUCLEAR_TRIGGER_CHANCE)
            if random.random() > chance * scale:
                continue

            used = min(launcher.nukes, max(1, launcher.nukes // 5))
            launcher.nukes -= used
            self._execute_nuclear_strike(launcher, target, used, world)
            break

    def _check_neutron_escalation(self, world=None, scale=1.0):
        """A desperate side may deploy neutron bombs when losing badly."""
        strength_map = {self.attacker: self.attacker.military_strength,
                        self.defender: self._defender_garrison}
        start_map    = {self.attacker: self._attacker_start,
                        self.defender: self._defender_start}
        for launcher, target in [(self.attacker, self.defender), (self.defender, self.attacker)]:
            if launcher.neutron_bombs <= 0:
                continue
            start = max(start_map[launcher], 1)
            strength_ratio = strength_map[launcher] / start
            if strength_ratio > 0.30:
                continue
            if random.random() > 0.12 * scale:
                continue
            launcher.neutron_bombs -= 1
            pop_loss = int(target.population * 0.15)
            mil_loss = target.military_strength * 0.20
            target.population = max(1, target.population - pop_loss)
            target.military_strength = max(0, target.military_strength - mil_loss)
            if target is self.defender:
                self._defender_garrison = max(0.0, self._defender_garrison - mil_loss)
            econ_hit = int(target.economy * 0.02)
            target.economy = max(1, target.economy - econ_hit)
            log(f"  [NEUTRON] \u2622 {launcher.name} deploys neutron bombs against {target.name}.")
            if world is not None:
                world.total_military_casualties += int(mil_loss)
                world.total_civilian_casualties += pop_loss
            from cities import pick_target_city
            city = pick_target_city(target)
            self.pending_strikes.append((
                launcher.name, target.name,
                city['name'] if city else None,
                city['lat']  if city else None,
                city['lon']  if city else None,
                1,
            ))
            break

    def _capture_territory(self):
        territory = self.contested_territory

        if territory not in self.defender.absorbed_names:
            if self.defender.absorbed_names:
                self.contested_territory = self.defender.absorbed_names[-1]
                remaining = len(self.defender.absorbed_names)
                self._defender_garrison = self.defender.military_strength / max(remaining, 1)
                self._defender_start    = max(self._defender_garrison, 1)
            return

        n    = len(self.defender.absorbed_names)
        frac = 1.0 / n

        econ_slice = int(self.defender.economy    * frac)
        pop_slice  = int(self.defender.population * frac)
        terr_slice = self.defender.territory      * frac

        self.attacker.economy    += econ_slice
        self.attacker.population += pop_slice
        self.attacker.territory  += terr_slice
        self.attacker.absorbed_names.append(territory)

        self.defender.economy    = max(1, self.defender.economy    - econ_slice)
        self.defender.population = max(1, self.defender.population - pop_slice)
        self.defender.territory  = max(0, self.defender.territory  - terr_slice)
        self.defender.absorbed_names.remove(territory)

        cost = int(self.attacker.military_strength * TERRITORY_CAPTURE_ATTACKER_COST)
        self.attacker.military_strength = max(1, self.attacker.military_strength - cost)

        self.attacker.war_exhaustion = min(1.0, self.attacker.war_exhaustion + 0.05)
        self.defender.war_exhaustion = min(1.0, self.defender.war_exhaustion + 0.08)

        flavor = random.choice(_TERRITORY_CAPTURE_FLAVORS).format(
            attacker=self.attacker.name, defender=self.defender.name, territory=territory
        )
        log(f"  >> {flavor}")

        remaining = len(self.defender.absorbed_names)
        self.contested_territory  = self.defender.absorbed_names[-1]
        self._defender_garrison   = self.defender.military_strength / max(remaining, 1)
        self._attacker_start      = max(self.attacker.military_strength, 1)
        self._defender_start      = max(self._defender_garrison, 1)

        if remaining == 1:
            flavor = random.choice(_TERRITORY_LAST_STAND_FLAVORS).format(
                attacker=self.attacker.name,
                defender=self.defender.name,
                territory=self.contested_territory,
            )
            log(f"  >> {flavor}")

    @property
    def is_over(self):
        if self.peace_deal is not None:
            return True
        # Minimum war duration: wars last at least 3 months regardless of military size
        if self.duration_days < MIN_WAR_DURATION:
            return False
        if self.attacker.military_strength <= 0:
            return True
        if self._defender_garrison <= 0 and len(self.defender.absorbed_names) <= 1:
            return True
        if not self.defender.absorbed_names:
            return True
        return False

    @property
    def winner(self):
        if self._peace_winner:
            return self._peace_winner
        if self.attacker.military_strength <= 0:
            return self.defender
        if self._defender_garrison <= 0 and len(self.defender.absorbed_names) <= 1:
            return self.attacker
        return None

    @property
    def loser(self):
        if self._peace_loser:
            return self._peace_loser
        if self.attacker.military_strength <= 0:
            return self.attacker
        if self._defender_garrison <= 0 and len(self.defender.absorbed_names) <= 1:
            return self.defender
        return None

    def __repr__(self):
        return f"Conflict({self.attacker.name} vs {self.defender.name}, day {self.duration_days})"
