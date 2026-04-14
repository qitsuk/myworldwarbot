import math
import random
from logger import log
from cities import pick_target_city, blast_radius_km, haversine_km, LETHAL_MORTALITY, DAMAGE_MORTALITY, fallout_duration_months

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

TERRITORY_CAPTURE_ATTACKER_COST = 0.12  # attacker loses 12% of current military as occupation cost per territory

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

        # The specific territory currently being fought over.
        # Wars progress territory by territory — most recently acquired falls first.
        self.contested_territory = defender.absorbed_names[-1]

        # Garrison = the share of the defender's military stationed in the contested territory.
        # Equal distribution: total / num_territories.  Attacker commits their full force.
        n = len(defender.absorbed_names)
        self._defender_garrison = defender.military_strength / max(n, 1)

        self._attacker_start = max(attacker.military_strength, 1)
        self._defender_start = max(self._defender_garrison, 1)

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

    def _guerrilla_strength(self, side, current_strength, start_strength):
        """Effective guerrilla contribution for a side that's taking heavy losses.
        Guerrillas are defenders — they fight for their homeland, not to invade.
        They emerge gradually as the regular military is ground down.
        current_strength is passed explicitly so garrison can be used for the defender."""
        desperation = max(0.0, 1.0 - current_strength / max(start_strength, 1))
        if desperation < GUERRILLA_THRESHOLD:
            return 0
        # Participation scales from 0 → GUERRILLA_RATE as losses go from threshold → 80%
        scale = min(1.0, (desperation - GUERRILLA_THRESHOLD) / (0.80 - GUERRILLA_THRESHOLD))
        civilians = max(0, side.population - side.military_strength)
        return int(civilians * GUERRILLA_RATE * scale * GUERRILLA_EFFICIENCY)

    def simulate_day(self, nation_count=999, endgame_threshold=2, world=None, scale=1.0):
        # scale < 1 for war sub-ticks: same total damage per month, spread over N steps
        self.duration_days += scale   # tracks real months regardless of sub-tick count

        attacker_roll = random.uniform(0.7, 1.3)
        defender_roll = random.uniform(0.7, 1.3)

        tech_ratio = self.attacker.tech_level / max(self.defender.tech_level, 0.1)

        # Attacker commits their full force.
        # Defender fights with the garrison of the contested territory only —
        # the rest of their army is holding other territories.
        attacker_str = self.attacker.military_strength
        defender_str = self._defender_garrison

        # Guerrillas supplement the losing side's defensive strength.
        # They're partially tech-resistant (terrain, concealment) so only half the tech
        # penalty applies to them — a guerrilla in the jungle is harder to bomb than a tank.
        attacker_guerrillas = self._guerrilla_strength(self.attacker, attacker_str,    self._attacker_start)
        defender_guerrillas = self._guerrilla_strength(self.defender, defender_str,    self._defender_start)
        attacker_effective  = attacker_str + attacker_guerrillas * (1 + (tech_ratio - 1) * 0.5)
        defender_effective  = defender_str + defender_guerrillas * (1 + (1 / tech_ratio - 1) * 0.5)

        attacker_losses = (defender_effective * 0.08) * attacker_roll * 1.2 / tech_ratio * scale
        defender_losses = (attacker_effective * 0.08) * defender_roll * 0.8 * tech_ratio * scale

        # Apply losses to attacker's total military
        attacker_mil_before = self.attacker.military_strength
        self.attacker.military_strength = max(0, self.attacker.military_strength - attacker_losses)
        self.attacker.military_strength = min(self.attacker.military_strength, self.attacker.military_cap)
        attacker_mil_lost = max(0, attacker_mil_before - self.attacker.military_strength)

        # Apply losses to the defender's garrison; sync the same loss to their total military
        garrison_before = self._defender_garrison
        self._defender_garrison = max(0.0, self._defender_garrison - defender_losses)
        actual_garrison_loss = garrison_before - self._defender_garrison
        self.defender.military_strength = max(0.0, self.defender.military_strength - actual_garrison_loss)

        if world is not None:
            world.total_military_casualties += int(attacker_mil_lost + actual_garrison_loss)

        # Civilian casualties — base rate plus extra for guerrilla fighters killed in action
        total_civ_lost = 0
        for side, guerrillas in ((self.attacker, attacker_guerrillas), (self.defender, defender_guerrillas)):
            guerrilla_dead = int(guerrillas * 0.08 * random.uniform(0.7, 1.3) * scale)
            pop_loss = int(side.population * CIVILIAN_CASUALTY_RATE * scale) + guerrilla_dead
            side.population = max(1, side.population - pop_loss)
            total_civ_lost += pop_loss
        if world is not None:
            world.total_civilian_casualties += total_civ_lost

        self._check_nuclear_escalation(nation_count, endgame_threshold, world, scale)
        if not self.peace_deal:
            self._check_peace_offer(scale)

        # Territory capture: garrison wiped out but defender still holds multiple territories —
        # transfer the contested territory and open a new front rather than ending the war.
        # Guard: attacker must still be standing (mutual destruction ≠ capture).
        if (not self.peace_deal
                and self.attacker.military_strength > 0
                and self._defender_garrison <= 0
                and len(self.defender.absorbed_names) > 1):
            self._capture_territory()

    def _check_peace_offer(self, scale=1.0):
        """Winning side may offer peace once the loser is desperate enough.

        For the defender, desperation is measured by garrison losses (they're only
        fighting with the troops in the contested territory, not their entire army).
        For the attacker, it's their total military.
        """
        # Use garrison for defender comparisons so peace triggers on battle momentum,
        # not on the defender's total national military
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

        # Only when the loser has dropped far enough
        if losing_strength > losing_start * PEACE_THRESHOLD:
            return
        if random.random() > PEACE_OFFER_CHANCE * scale:
            return

        flavor = random.choice(_PEACE_OFFER_FLAVORS).format(winner=winning.name, loser=losing.name)
        log(f"  [PEACE] {flavor}")

        # Loser's roll — desperation increases acceptance
        desperation   = 1.0 - losing_strength / max(losing_start, 1)
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

    def _execute_nuclear_strike(self, launcher, target, used, world):
        """Apply one nuclear salvo: damage, logging, pending strike, collateral."""
        launcher.nuked   = True
        target.was_nuked = True
        if world is not None:
            world.total_nukes_used += used

        city      = pick_target_city(target)
        city_name = city['name'] if city else None
        city_lat  = city['lat']  if city else None
        city_lon  = city['lon']  if city else None

        self.pending_strikes.append((launcher.name, target.name, city_name, city_lat, city_lon, used))

        city_str = f" ({city_name})" if city_name else ""
        flavor = random.choice(_NUCLEAR_LAUNCH_FLAVORS).format(
            launcher=launcher.name, used=used, target=target.name)
        log(f"  [NUCLEAR] \u2622 {flavor}{city_str}")

        # ── Damage model ─────────────────────────────────────────────────
        # When a specific city is targeted, damage is calculated at city
        # scale (warheads per million city residents) — so 12 warheads on
        # Hiroshima devastates the city, not 12÷127M of Japan.
        # The city-level destruction is then scaled back to national impact
        # by the city's share of the nation's population, with military and
        # economy weighted higher (both concentrate in cities).
        # Without a city target, fall back to national density.

        def sat(density, cap, scale):
            return cap * (1.0 - math.exp(-density / scale))

        if city:
            city_pop_M      = max(city.get('pop', 0.1), 0.01)   # millions
            city_density    = used / city_pop_M

            # Destruction of the city itself
            city_pop_frac   = sat(city_density, 0.90, 1.0)  # up to 90 % of city killed
            city_mil_frac   = sat(city_density, 0.95, 0.8)  # military installations levelled
            city_econ_frac  = sat(city_density, 0.95, 0.8)  # infrastructure annihilated

            # City's share of the nation — forces and industry concentrate in cities
            city_share_pop  = min(1.0, city_pop_M * 1_000_000 / max(target.population, 1))
            city_share_mil  = min(1.0, city_share_pop * 3.0)   # troops near cities
            city_share_econ = min(1.0, city_share_pop * 2.5)   # economic hubs

            tgt_pop_frac    = city_pop_frac  * city_share_pop
            tgt_mil_frac    = city_mil_frac  * city_share_mil
            tgt_econ_frac   = city_econ_frac * city_share_econ
        else:
            # No city data — scattered / area strike, use national density
            nation_pop_M  = max(target.population / 1_000_000, 0.01)
            nation_density = used / nation_pop_M
            tgt_mil_frac  = sat(nation_density, 0.92, 2.0)
            tgt_pop_frac  = sat(nation_density, 0.55, 2.5)
            tgt_econ_frac = sat(nation_density, 0.88, 3.0)

        mil_before  = target.military_strength
        pop_before  = target.population
        econ_before = target.economy

        target.military_strength = max(0, target.military_strength * (1.0 - tgt_mil_frac))
        target.population        = max(1, int(target.population    * (1.0 - tgt_pop_frac)))
        target.economy           = max(0, int(target.economy       * (1.0 - tgt_econ_frac)))

        mil_lost  = int(mil_before - target.military_strength)
        pop_lost  = pop_before - target.population
        econ_lost = econ_before - target.economy
        if world is not None:
            world.total_military_casualties += mil_lost
            world.total_civilian_casualties  += pop_lost

        # Severity label: use city-level destruction when available, since a
        # large nation can absorb a city strike nationally but the city itself
        # is still obliterated.
        severity_frac = city_pop_frac if city else tgt_mil_frac
        if severity_frac < 0.15:   severity = "Limited"
        elif severity_frac < 0.40: severity = "Significant"
        elif severity_frac < 0.65: severity = "Severe"
        elif severity_frac < 0.82: severity = "Devastating"
        else:                      severity = "Apocalyptic"

        city_note = f" — {city_name} obliterated" if city and city_pop_frac > 0.75 else ""
        log(f"  [NUCLEAR] \u2622 {severity} strike ({used} warheads) on {target.name}{city_note} — "
            f"{mil_lost:,} troops, {pop_lost:,} civilians, \u20ac{econ_lost:,} economy lost.")

        if city and world is not None:
            lethal_km, damage_km = blast_radius_km(used)
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
                         casualties, bcity['lat'], bcity['lon'], used)
                    )
                    log(f"  [NUCLEAR] \u2622 Collateral: {bcity['name']} ({bystander.name}) struck by fallout — "
                        f"{casualties:,} casualties ({dist:.0f} km from {city_name})")

    def trigger_opening_strike(self, world):
        """Nuclear first strike fired the moment war is declared.

        Called when a nuclear-armed aggressor picks a fight they couldn't win
        conventionally — they open with warheads to soften the target before
        troops cross the border.
        """
        if self.attacker.nukes <= 0:
            return
        # Use up to 30 % of the arsenal, minimum 1
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

    def _capture_territory(self):
        """Transfer the contested territory from defender to attacker and open the next front.

        The garrison was already depleted to 0 during combat (and the defender's total
        military was synced down by the same losses), so no separate military deduction
        is needed here.  The new garrison is naturally the defender's remaining military
        spread equally across their remaining territories.
        """
        territory = self.contested_territory  # the territory whose garrison just fell

        # Guard: another simultaneous conflict may have already taken this territory.
        # Re-sync to whatever the defender still holds and bail out.
        if territory not in self.defender.absorbed_names:
            if self.defender.absorbed_names:
                self.contested_territory = self.defender.absorbed_names[-1]
                remaining = len(self.defender.absorbed_names)
                self._defender_garrison = self.defender.military_strength / max(remaining, 1)
                self._defender_start    = max(self._defender_garrison, 1)
            return

        n    = len(self.defender.absorbed_names)
        frac = 1.0 / n

        # Transfer proportional resources
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

        # Attacker pays an occupation cost — garrisoning newly taken land is expensive
        cost = int(self.attacker.military_strength * TERRITORY_CAPTURE_ATTACKER_COST)
        self.attacker.military_strength = max(1, self.attacker.military_strength - cost)

        # Accumulate war exhaustion per territory captured
        self.attacker.war_exhaustion = min(1.0, self.attacker.war_exhaustion + 0.05)
        self.defender.war_exhaustion = min(1.0, self.defender.war_exhaustion + 0.08)

        flavor = random.choice(_TERRITORY_CAPTURE_FLAVORS).format(
            attacker=self.attacker.name, defender=self.defender.name, territory=territory
        )
        log(f"  >> {flavor}")

        # Open the next front: new contested territory + garrison = equal share of remaining
        remaining = len(self.defender.absorbed_names)
        self.contested_territory  = self.defender.absorbed_names[-1]
        self._defender_garrison   = self.defender.military_strength / max(remaining, 1)
        self._attacker_start      = max(self.attacker.military_strength, 1)
        self._defender_start      = max(self._defender_garrison, 1)

        # Last-stand notice when only the homeland remains
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
        if self.attacker.military_strength <= 0:
            return True
        # Garrison wiped with one territory left = final defeat
        if self._defender_garrison <= 0 and len(self.defender.absorbed_names) <= 1:
            return True
        # Defender has no territories left (stripped by other simultaneous conflicts)
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
