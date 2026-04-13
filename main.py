import math
import os
import time
import random
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv
from data_loader import load_countries, load_events
from world import World
from conflict import Conflict, PYRRHIC_RATIO, _PEACE_PYRRHIC_FLAVORS
from alliance import Alliance
from logger import log
from data_loader import DATA_YEAR

load_dotenv(Path(__file__).parent / '.env')

VOWELS = set('aeiouAEIOU')

TIMESCALE_TEST = 0.5
TIMESCALE_PROD = 1 * 60 * 60  # 1 hour per month

INVASION_THRESHOLD = 10.0
ALLIANCE_CHANCE       = 0.002  # chance per month an unaligned country seeks an alliance
ALLIANCE_DECAY_CHANCE = 0.008  # chance per member per month to defect
MAX_ALLIANCE_SIZE     = 6      # hard cap on members per alliance

PEACETIME_ARMY_BASE   = 0.012  # minimum standing army: 1.2% of population
PEACETIME_ARMY_SCALE  = 0.04   # each point of world.risk adds this × population to the target
WARTIME_ARMY_TARGET   = 0.40   # nations mobilise toward 40% of military_cap during war
RECRUITMENT_RATE      = 0.04   # close 4% of the gap to target each month
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

PEACE_MONTHS      = 42    # no wars for the first 3.5 years
RAMP_MONTHS       = 24    # risk ramps 0 → BASE_RISK over the following 2 years
BASE_RISK         = 0.15
RISK_ESCALATION   = 0.0004  # risk grows by this much per month after the ramp ends
MAX_RISK          = 0.70    # hard ceiling
STALEMATE_MONTHS  = 36    # if no new conflict starts in this many months, force one

# Nuclear proliferation thresholds
NUKE_TECH_THRESHOLD  = 2.8   # minimum tech_level to begin enrichment
NUKE_RISK_THRESHOLD  = 0.25  # world.risk must exceed this before any enrichment starts
NUKE_MAX_STOCKPILE   = 4999  # cap to exclude Russia/USA-tier arsenals (>= 5000)
URANIUM_PER_NUKE     = 12.0  # enrichment units needed to build one warhead
URANIUM_RATE_BASE    = 0.04  # base units accumulated per month when enriching
# enrichment rate scales with tech: base × (tech / NUKE_TECH_THRESHOLD) up to ×2
URANIUM_RATE_MAX_MULT = 2.0

START_YEAR = random.randint(2027, 2150)
START_DATE = date(START_YEAR, 1, 1)

_default_timescale = TIMESCALE_TEST if DEBUG else TIMESCALE_PROD
sleep_time = float(os.getenv('TIMESCALE', _default_timescale))

def current_date(world):
    """Each simulation tick = 1 month. Returns the 1st of the corresponding month."""
    months = world.current_day - 1
    year  = START_DATE.year + (START_DATE.month - 1 + months) // 12
    month = (START_DATE.month - 1 + months) % 12 + 1
    return date(year, month, 1)

def find_absorber(dead_country, world, exclude=None):
    """Find the active country that absorbed a dead country's territories."""
    for c in world.countries:
        if c is not exclude and any(n in c.absorbed_names for n in dead_country.absorbed_names):
            return c
    return None

def annexe(winner, loser, world):
    if loser not in world.countries:
        return

    # If winner was already eliminated this same tick, redirect to whoever absorbed them
    if winner not in world.countries:
        winner = find_absorber(winner, world, exclude=loser)
        if winner is None:
            # No absorber found — just remove the loser silently
            world.countries.remove(loser)
            return

    winner.economy += loser.economy
    winner.population += loser.population
    winner.territory += loser.territory
    winner.neighbors = list(set(winner.neighbors + loser.neighbors) - {winner.name})
    winner.military_strength = min(winner.military_strength, winner.military_cap)
    winner.absorbed_names.extend(loser.absorbed_names)
    winner.nukes     += loser.nukes
    winner.uranium   += loser.uranium
    winner.nuked      = winner.nuked     or loser.nuked
    winner.was_nuked  = winner.was_nuked or loser.was_nuked
    world.countries.remove(loser)
    flavor = random.choice(_WAR_ANNEXATION_FLAVORS).format(winner=winner.name, loser=loser.name)
    log(f"  >> {flavor}")

    # Clean loser out of any alliance
    for alliance in list(world.alliances):
        if alliance.has_member(loser):
            alliance.remove_member(loser)
            if len(alliance.members) < 2:
                world.alliances.remove(alliance)

def blend_country_names(a, b):
    """Create a portmanteau from two country names (e.g. Pakistan + Afghanistan = Pakighanistan)."""
    # Take ~1/4 of A, extended forward to end on a vowel
    cut_a = max(2, len(a) // 4)
    for i in range(cut_a, min(len(a) - 1, cut_a + 4)):
        if a[i] in VOWELS:
            cut_a = i + 1
            break

    # Start ~1/4 into B, adjusted to begin on a consonant
    cut_b = max(1, len(b) // 4)
    for i in range(cut_b, min(len(b) - 1, cut_b + 3)):
        if b[i] not in VOWELS:
            cut_b = i
            break

    pa, pb = a[:cut_a], b[cut_b:]

    # Avoid duplicate consonants at the junction (e.g. "Fr" + "rmany" → "Frmany")
    if pa and pb and pa[-1].lower() == pb[0].lower() and pa[-1].lower() not in VOWELS:
        pb = pb[1:]

    result = pa + pb
    return result[0].upper() + result[1:] if result else ''

def get_valid_neighbors(country, world):
    existing_names = {c.name for c in world.countries}
    return [c for c in world.countries if c.name in country.neighbors and c.name in existing_names]

def get_targets(country, world):
    valid = get_valid_neighbors(country, world)
    if valid:
        return valid
    others = [c for c in world.countries if c != country]
    return random.sample(others, min(3, len(others)))

def get_alliance(country, world):
    for alliance in world.alliances:
        if alliance.has_member(country):
            return alliance
    return None

GIANT_PERCENTILE = 0.15   # top 15% by military_cap are giants; they cannot ally

_ALLIANCE_FORM_FLAVORS = [
    "{a} and {b} sign a mutual defence pact.",
    "Diplomats in {a} and {b} seal a historic agreement.",
    "{a} and {b} find common cause against a dangerous world.",
    "A new axis emerges: {a} and {b} pledge their swords together.",
    "{a} extends an olive branch to {b} — and {b} accepts.",
    "Bound by shared fears, {a} and {b} unite.",
    "The flags of {a} and {b} fly side by side for the first time.",
    "Pragmatism wins out: {a} and {b} agree to stand together.",
    "In a surprise move, {a} and {b} announce a formal alliance.",
    "Quiet negotiations between {a} and {b} produce a landmark treaty.",
    "What began as rivalry ends in partnership: {a} and {b} ally.",
    "Strategic interests align as {a} and {b} forge a new pact.",
    "The world watches as {a} and {b} declare themselves allies.",
    "{a} reaches across the border to {b}, finding a willing partner.",
    "A bloc is born: {a} and {b} commit to mutual protection.",
    "Faced with rising dangers, {a} and {b} choose cooperation.",
    "{a} and {b} ink a non-aggression and mutual aid treaty.",
    "Old tensions dissolve as {a} and {b} formally align.",
    "Hardened by instability, {a} and {b} turn to one another.",
    "A pact in troubled times: {a} and {b} join forces.",
    "Diplomacy triumphs as {a} and {b} agree to defend each other.",
    "Neither alone nor afraid — {a} and {b} stand together.",
    "{a} and {b} choose solidarity over isolation.",
    "United by necessity, {a} and {b} forge an unlikely alliance.",
    "The ink is barely dry: {a} and {b} have allied.",
]

_ALLIANCE_BREAK_FLAVORS = [
    "{country} withdraws from {alliance}, citing irreconcilable differences.",
    "The {alliance} fractures as {country} walks away.",
    "{country} quietly exits {alliance}, ending its commitment.",
    "Citing shifting priorities, {country} leaves {alliance}.",
    "The pact strains and breaks: {country} parts ways with {alliance}.",
    "{country} tears up its treaty with {alliance}.",
    "Disillusioned, {country} abandons {alliance}.",
    "{country} declares it will no longer be bound by {alliance}.",
    "A blow to solidarity: {country} defects from {alliance}.",
    "Diplomatic ties fray as {country} exits {alliance}.",
    "{country} concludes that {alliance} no longer serves its interests.",
    "The {alliance} loses a member as {country} steps back.",
    "{country} goes it alone, withdrawing from {alliance}.",
    "Once allies, now strangers: {country} breaks from {alliance}.",
    "Internal tensions boil over as {country} quits {alliance}.",
    "{country} pulls its forces from {alliance} without explanation.",
    "Amid growing mistrust, {country} leaves {alliance}.",
    "The bloc weakens: {country} has abandoned {alliance}.",
    "{country} signals a new direction, departing from {alliance}.",
    "Self-interest wins out — {country} withdraws from {alliance}.",
    "The ink on the {alliance} treaty fades as {country} exits.",
    "{country} no longer stands with {alliance}.",
    "A quiet but damaging blow: {country} defects from {alliance}.",
    "Pragmatism turns to betrayal as {country} leaves {alliance}.",
    "{country} charts its own course, abandoning {alliance}.",
]

_WAR_DECLARATION_FLAVORS = [
    "{attacker} crosses the border into {defender} — war has begun.",
    "Without warning, {attacker} launches an offensive against {defender}.",
    "The drums of war sound as {attacker} mobilises against {defender}.",
    "{attacker} has had enough — it strikes at {defender}.",
    "Negotiations have failed. {attacker} moves against {defender}.",
    "{attacker} opens a new front against {defender}.",
    "Tensions boil over as {attacker} invades {defender}.",
    "The order is given: {attacker} attacks {defender}.",
    "{attacker} seizes the initiative and strikes {defender}.",
    "A bold gamble: {attacker} goes to war with {defender}.",
    "{attacker} breaks the peace and declares war on {defender}.",
    "Citing grievances old and new, {attacker} wages war on {defender}.",
    "{attacker} sends its forces marching into {defender}.",
    "Diplomacy is dead. {attacker} declares war on {defender}.",
    "The conflict was coming — {attacker} simply fires the first shot against {defender}.",
]

_WAR_INSTANT_FLAVORS = [
    "Resistance crumbles. {attacker} sweeps through {defender} unopposed.",
    "{defender} collapses before {attacker}'s overwhelming might.",
    "{attacker} rolls over {defender} in a matter of days.",
    "Outgunned and outnumbered, {defender} falls to {attacker} without a fight.",
    "{defender} never stood a chance. {attacker} seizes it in a single stroke.",
    "A swift campaign: {attacker} conquers {defender} without breaking a sweat.",
    "The outcome was never in doubt. {attacker} takes {defender}.",
    "{attacker}'s forces pour into {defender}, meeting almost no resistance.",
    "In a lightning strike, {attacker} annexes {defender}.",
    "The campaign is brief and brutal — {attacker} absorbs {defender}.",
]

_WAR_TECH_DEFIANCE_FLAVORS = [
    "{defender}'s advanced arsenal defies {attacker}'s numerical advantage.",
    "Technology bridges the gap — {defender} refuses to yield to {attacker}.",
    "{defender} fights on, its superior weapons holding {attacker} at bay.",
    "{attacker} is larger, but {defender} is smarter. The fight continues.",
    "Quality over quantity: {defender} stands firm against {attacker}.",
    "{defender}'s cutting-edge military gives its soldiers renewed resolve.",
    "Outnumbered but never outmatched, {defender} fights back against {attacker}.",
    "{attacker}'s numbers mean little against {defender}'s technological edge.",
    "Armed with advanced weaponry, {defender} refuses to bow to {attacker}.",
    "Against all odds, {defender} leverages its tech edge to hold off {attacker}.",
]

_WAR_BRAVE_RESISTANCE_FLAVORS = [
    "Hopelessly outnumbered, {defender} fights on regardless.",
    "{defender} refuses to kneel before {attacker}.",
    "Against overwhelming odds, {defender} stands its ground.",
    "{attacker} expected a quick surrender. {defender} had other ideas.",
    "Outgunned but defiant, {defender} will not yield to {attacker}.",
    "{defender} digs in — it will not be taken without a fight.",
    "Pride and desperation drive {defender} to resist {attacker}.",
    "The people of {defender} take up arms, refusing to submit to {attacker}.",
    "{defender} will fall — but not without costing {attacker} dearly.",
    "No surrender. {defender} vows to resist {attacker} to the last soldier.",
]

_WAR_ALLIANCE_ENTRY_FLAVORS = [
    "{ally} honours its treaty and enters the war against {attacker}.",
    "True to its word, {ally} rides to {defender}'s defence.",
    "The war widens: {ally} declares war on {attacker} in solidarity with {defender}.",
    "{ally} invokes its alliance with {defender} and joins the fight.",
    "A new front opens as {ally} rushes to the aid of {defender}.",
    "{ally} will not stand by while {defender} is attacked — it enters the war.",
    "Bound by treaty, {ally} turns its guns on {attacker}.",
    "{attacker} now faces a second enemy: {ally} stands with {defender}.",
    "The conflict escalates as {ally} enters on the side of {defender}.",
    "{ally} marches to war, unwilling to abandon {defender}.",
    "{ally} answers the call — {defender} will not fight {attacker} alone.",
    "Honour demands it: {ally} joins {defender} against {attacker}.",
]

_WAR_ANNEXATION_FLAVORS = [
    "{winner} raises its flag over what was once {loser}.",
    "{loser} ceases to exist — absorbed entirely by {winner}.",
    "The nation of {loser} is no more. {winner} claims its lands.",
    "{winner} consolidates its gains, formally annexing {loser}.",
    "{loser} is erased from the map by {winner}.",
    "By right of conquest, {winner} absorbs {loser}.",
    "The borders are redrawn: {loser} becomes part of {winner}.",
    "{loser}'s sovereignty ends today. {winner} takes all.",
    "{winner} plants its banner across {loser}. The conquest is complete.",
    "Defiant to the last, {loser} falls to {winner}.",
    "A nation disappears: {loser} is folded into {winner}.",
    "{winner} finishes what it started — {loser} is gone.",
]

_WAR_BETRAYAL_FLAVORS = [
    "{attacker} shatters the alliance and turns on {defender}.",
    "Former friends become enemies: {attacker} attacks {defender}.",
    "Trust is the first casualty — {attacker} strikes at {defender}.",
    "{defender} never saw it coming. {attacker} attacks without warning.",
    "Alliances mean nothing now. {attacker} goes to war with {defender}.",
    "In the final chapter, even friends become enemies: {attacker} turns on {defender}.",
    "The grand betrayal: {attacker} turns its weapons on {defender}.",
    "Honour means nothing at the end of the world. {attacker} attacks {defender}.",
    "{attacker} decides that cooperation is for the weak, and attacks {defender}.",
    "The alliance dissolves in bloodshed as {attacker} betrays {defender}.",
]

_NUCLEAR_ENRICHMENT_FLAVORS = [
    "Satellites detect unusual heat signatures near {country}'s remote facilities.",
    "{country} quietly begins enriching uranium — the world watches nervously.",
    "Intelligence analysts flag suspicious centrifuge activity in {country}.",
    "Under the guise of civilian energy, {country} accelerates its enrichment programme.",
    "{country}'s engineers work in shifts around the clock at an undisclosed facility.",
    "Diplomatic cables warn that {country} is on the path to the bomb.",
    "Inspectors are turned away at the border as {country} ramps up enrichment.",
    "{country} withdraws from non-proliferation discussions without explanation.",
    "Trace isotopes in {country}'s atmosphere suggest an active weapons programme.",
    "World powers demand answers — {country} stays silent and keeps enriching.",
]

_NUCLEAR_PROLIFERATION_FLAVORS = [
    "{country} joins the nuclear club — the world grows more dangerous.",
    "Intelligence sources confirm: {country} has the bomb.",
    "{country} successfully tests its first nuclear device.",
    "The world's strategic balance shifts as {country} goes nuclear.",
    "In secret labs, {country} has built what it hopes will guarantee its survival.",
    "{country} adds the ultimate deterrent to its arsenal.",
    "Fears of proliferation are realised — {country} now has nuclear weapons.",
    "A new nuclear power emerges from the shadows: {country}.",
    "{country}'s nuclear programme, long suspected, has borne fruit.",
    "The unthinkable becomes reality: {country} has developed nuclear weapons.",
]

_NUCLEAR_MILESTONE_FLAVORS = [
    "{country}'s nuclear arsenal quietly crosses {n} warheads.",
    "Arms control experts warn: {country} now fields {n} nuclear weapons.",
    "{country} reaches {n} warheads — a regional deterrent is now a global one.",
    "With {n} warheads, {country} cements itself as a nuclear middle power.",
    "The proliferation crisis deepens as {country} surpasses {n} warheads.",
]

_UNION_FLAVORS = [
    "{a} and {b} lay down their differences and emerge as {name}.",
    "A new nation is born from the fires of war: {name}.",
    "Out of conflict comes unity — {a} and {b} become {name}.",
    "The borders are redrawn as {a} and {b} merge into {name}.",
    "{a} and {b} find more in common than in conflict, forming {name}.",
    "History is written today: {a} and {b} unite as {name}.",
    "From two, one: {name} rises from the merger of {a} and {b}.",
    "The war ends not with a victor, but a new nation: {name}.",
    "In a remarkable turn, {a} and {b} set aside the past and become {name}.",
    "Neither conquered nor vanquished — {a} and {b} simply become {name}.",
]

_WORLD_PEACE_ENDS_FLAVORS = [
    "The long peace is over. Nations begin to mobilise for what comes next.",
    "The era of tranquility ends — the world shifts uneasily into a new age.",
    "Militaries stir and borders tense. The peace cannot hold much longer.",
    "The world held its breath long enough. Armies begin to march.",
    "Stability gives way to ambition — the quiet years are ending.",
    "A fragile peace begins to crack as nations look beyond their borders.",
    "The long calm has bred restlessness. Something is coming.",
    "After years of peace, the drumbeats of war begin to sound.",
]

_WORLD_TENSIONS_PEAK_FLAVORS = [
    "Global tensions have reached a fever pitch. War seems unavoidable.",
    "The world teeters on the edge — full-scale conflict is only a spark away.",
    "Diplomacy has failed everywhere. The world braces for the worst.",
    "Fear and ambition grip every capital. The age of war has truly begun.",
    "No corner of the globe is safe from the shadow of conflict.",
    "The world has never been more dangerous. Leaders pray for peace — few believe in it.",
    "Lines are drawn, armies are massed — the great war approaches.",
    "The balance of power strains to breaking point. Conflict is imminent.",
]

_WORLD_FINAL_FRACTURE_FLAVORS = [
    "Only allied nations remain. The grand alliance fractures — and the final war begins.",
    "With no enemies left to unite them, the great alliance tears itself apart.",
    "The last alliance splinters. Former allies raise their swords against each other.",
    "Peace could not last among the powerful. The grand coalition collapses into civil war.",
    "Allies become enemies as the final chapter of this world begins.",
    "The great powers, once united, now turn on each other in a final reckoning.",
    "The world's last alliance dissolves — only war remains.",
    "Brotherhood lasts only so long. The alliance fractures and the end begins.",
]

_STALEMATE_FLAVORS = [
    "Peace grows stale. {aggressor} breaks the silence and attacks {target}.",
    "A long calm is shattered as {aggressor} turns aggressive toward {target}.",
    "Boredom and ambition collide: {aggressor} launches a campaign against {target}.",
    "The world had almost forgotten war — {aggressor} reminds {target}.",
    "Restless and hungry, {aggressor} makes its move against {target}.",
    "Stability breeds complacency. {aggressor} exploits it, striking {target}.",
    "After months of quiet, {aggressor} tears it all apart, attacking {target}.",
    "The peace was always fragile. {aggressor} finally shatters it, striking {target}.",
    "Seeing an opportunity in the calm, {aggressor} strikes {target} without warning.",
    "Patience runs thin in {aggressor} — it launches an attack on {target}.",
]

_ALLIANCE_JOIN_FLAVORS = [
    "{country} seeks shelter under the banner of {alliance}.",
    "{country} petitions to join {alliance} — and is welcomed.",
    "The {alliance} grows stronger as {country} joins its ranks.",
    "{country} pledges its forces to {alliance}.",
    "Seeking safety in numbers, {country} joins {alliance}.",
    "{country} throws its lot in with {alliance}.",
    "A new member swells the ranks of {alliance}: {country}.",
    "{country} signs on to {alliance}, bringing fresh strength to the bloc.",
    "Not wishing to stand alone, {country} joins {alliance}.",
    "{country} finds common cause with the members of {alliance}.",
    "The {alliance} welcomes {country} as its newest member.",
    "{country} extends its hand to {alliance} — and is embraced.",
    "Bolstered by {country}, {alliance} grows ever stronger.",
    "{country} commits its armies to the {alliance} cause.",
    "Outnumbered and wary, {country} seeks refuge in {alliance}.",
    "The pact expands: {country} is now part of {alliance}.",
    "Mutual interests draw {country} toward {alliance}.",
    "{alliance} adds {country} to its roster of allies.",
    "After careful deliberation, {country} casts its fate with {alliance}.",
    "{country} plants its flag alongside those of {alliance}.",
    "A quiet ceremony marks {country}'s entry into {alliance}.",
    "{country} and {alliance} formalise their cooperation.",
    "The world shifts: {country} has joined {alliance}.",
    "{country} raises the banner of {alliance}.",
    "No longer isolated, {country} marches under the {alliance} flag.",
]

def get_giant_threshold(world):
    caps = sorted(c.military_cap for c in world.countries)
    idx  = int(len(caps) * (1 - GIANT_PERCENTILE))
    return caps[max(idx, 0)]

def form_alliances(world):
    giant_threshold = get_giant_threshold(world)
    at_war_set = {c.attacker for c in world.active_conflicts} | {c.defender for c in world.active_conflicts}

    for country in list(world.countries):
        if get_alliance(country, world):
            continue
        if country.military_cap >= giant_threshold:
            continue
        if country in at_war_set:
            continue
        if random.random() > ALLIANCE_CHANCE:
            continue

        # Existing alliances this country could join (not full, no giants, not at war with any member)
        joinable = [
            a for a in world.alliances
            if len(a.members) < MAX_ALLIANCE_SIZE
            and all(m.military_cap < giant_threshold for m in a.members)
            and not any(m in at_war_set for m in a.members)
            and not any(
                (c.attacker == country and c.defender in a.members) or
                (c.attacker in a.members and c.defender == country)
                for c in world.active_conflicts
            )
        ]

        # Unaligned non-giant countries this country could partner with
        unaligned = [
            c for c in world.countries
            if not get_alliance(c, world)
            and c != country
            and c.military_cap < giant_threshold
            and c not in at_war_set
            and not any(
                (cf.attacker == country and cf.defender == c) or
                (cf.attacker == c and cf.defender == country)
                for cf in world.active_conflicts
            )
        ]

        if not joinable and not unaligned:
            continue

        # Weight alliances by size × avg member strength (safety in numbers),
        # weight unaligned candidates by their military_cap
        options  = joinable + unaligned
        weights  = (
            [len(a.members) * (sum(m.military_cap for m in a.members) / len(a.members)) + 1
             for a in joinable] +
            [c.military_cap + 1 for c in unaligned]
        )
        chosen = random.choices(options, weights=weights, k=1)[0]

        if isinstance(chosen, Alliance):
            chosen.members.append(country)
            flavor = random.choice(_ALLIANCE_JOIN_FLAVORS).format(country=country.name, alliance=chosen.name)
            log(f"  [ALLIANCE] {flavor}")
        else:
            world.alliances.append(Alliance([country, chosen]))
            flavor = random.choice(_ALLIANCE_FORM_FLAVORS).format(a=country.name, b=chosen.name)
            log(f"  [ALLIANCE] {flavor}")

def decay_alliances(world):
    """Each month, members may defect from their alliance."""
    for alliance in list(world.alliances):
        # Prune members no longer in the world
        for member in list(alliance.members):
            if member not in world.countries:
                alliance.remove_member(member)

        for member in list(alliance.members):
            if random.random() > ALLIANCE_DECAY_CHANCE:
                continue
            old_name = alliance.name
            alliance.remove_member(member)
            flavor = random.choice(_ALLIANCE_BREAK_FLAVORS).format(country=member.name, alliance=old_name)
            log(f"  [ALLIANCE] {flavor}")

        if len(alliance.members) < 2 and alliance in world.alliances:
            world.alliances.remove(alliance)

def check_final_war(world):
    """If every surviving nation is in an alliance, fracture them and force the final war."""
    if len(world.countries) <= 1 or world.active_conflicts:
        return
    # If any nation is unallied, war can start naturally — nothing to do
    if any(get_alliance(c, world) is None for c in world.countries):
        return

    log(f"  [WORLD] {random.choice(_WORLD_FINAL_FRACTURE_FLAVORS)}")
    world.alliances.clear()

    # Pair nations by military strength and start conflicts
    remaining = sorted(world.countries, key=lambda c: c.military_strength, reverse=True)
    paired = set()
    for i, a in enumerate(remaining):
        if a in paired:
            continue
        for b in remaining[i + 1:]:
            if b in paired:
                continue
            world.active_conflicts.append(Conflict(a, b))
            flavor = random.choice(_WAR_BETRAYAL_FLAVORS).format(attacker=a.name, defender=b.name)
            log(f"  >> {flavor}")
            paired.add(a)
            paired.add(b)
            break
    # Any unpaired nation (odd count) attacks the strongest
    for c in remaining:
        if c not in paired:
            world.active_conflicts.append(Conflict(c, remaining[0]))
            flavor = random.choice(_WAR_BETRAYAL_FLAVORS).format(attacker=c.name, defender=remaining[0].name)
            log(f"  >> {flavor}")

def trigger_alliance_support(attacker, defender, world):
    alliance = get_alliance(defender, world)
    if not alliance:
        return
    for ally in alliance.get_allies(defender):
        if ally not in world.countries:
            continue
        already_fighting = any(
            c.attacker == ally or c.defender == ally
            for c in world.active_conflicts
        )
        if already_fighting:
            continue
        conflict = Conflict(ally, attacker)
        world.active_conflicts.append(conflict)
        flavor = random.choice(_WAR_ALLIANCE_ENTRY_FLAVORS).format(ally=ally.name, defender=defender.name, attacker=attacker.name)
        log(f"  >> {flavor}")

def merge_countries(primary, secondary, world):
    if secondary not in world.countries or primary not in world.countries:
        return
    old_name = primary.name
    merged_name = blend_country_names(primary.name, secondary.name)
    primary.name = merged_name
    primary.economy += secondary.economy
    primary.population += secondary.population
    primary.territory += secondary.territory
    primary.neighbors = list(set(primary.neighbors + secondary.neighbors) - {merged_name})
    primary.military_strength = min(
        primary.military_strength + secondary.military_strength,
        primary.military_cap
    )
    primary.absorbed_names.extend(secondary.absorbed_names)
    primary.nukes     += secondary.nukes
    primary.uranium   += secondary.uranium
    primary.was_nuked  = primary.was_nuked or secondary.was_nuked
    primary.nuked = primary.nuked or secondary.nuked
    primary.tech_level = round(max(primary.tech_level, secondary.tech_level), 2)
    world.countries.remove(secondary)
    flavor = random.choice(_UNION_FLAVORS).format(a=old_name, b=secondary.name, name=merged_name)
    log(f"  [UNION] {flavor}")


def get_world_state(world):
    at_war_names = set()
    for c in world.active_conflicts:
        at_war_names.add(c.attacker.name)
        at_war_names.add(c.defender.name)

    alliance_id_map = {}
    for i, alliance in enumerate(world.alliances):
        for member in alliance.members:
            alliance_id_map[member.name] = i

    top5 = sorted(world.countries, key=lambda c: c.military_strength, reverse=True)[:5]

    # territory_info: original country name → {color, owner name, at war, in alliance}
    # This lets the frontend color absorbed territories with the annexing country's color.
    territory_info = {}
    for country in world.countries:
        entry = {
            'c': country.color,
            'o': country.name,
            'w': country.name in at_war_names,
            'a': country.name in alliance_id_map,
        }
        for orig_name in country.absorbed_names:
            territory_info[orig_name] = entry

    return {
        'day': world.current_day,
        'date': current_date(world).strftime('%B %d, %Y'),
        'risk': round(world.risk, 4),
        'total_countries': len(world.countries),
        'world_population': sum(c.population for c in world.countries),
        'countries': [
            {
                'name': c.name,
                'military': int(c.military_strength),
                'military_cap': int(c.military_cap),
                'economy': int(c.economy),
                'population': int(c.population),
                'at_war': c.name in at_war_names,
                'alliance_id': alliance_id_map.get(c.name),
                'absorbed_names': c.absorbed_names,
                'nukes': c.nukes,
                'nuked': c.nuked,
                'was_nuked': c.was_nuked,
                'tech_level': round(c.tech_level, 2),
            }
            for c in world.countries
        ],
        'conflicts': [
            {
                'attacker':        c.attacker.name,
                'defender':        c.defender.name,
                'day':             c.duration_days,
                'attacker_str':    int(c.attacker.military_strength),
                'defender_str':    int(c._defender_garrison),        # garrison in contested territory
                'defender_total':  int(c.defender.military_strength), # defender's full national military
                'attacker_start':  int(c._attacker_start),
                'defender_start':  int(c._defender_start),
                'contested':       c.contested_territory,
            }
            for c in world.active_conflicts
        ],
        'alliances': [
            [m.name for m in a.members]
            for a in world.alliances
        ],
        'top5': [
            {
                'name': c.name,
                'military': int(c.military_strength),
                'military_cap': int(c.military_cap),
                'color': c.color,
                'nukes': c.nukes,
            }
            for c in top5
        ],
        'territory_info': territory_info,
    }

def print_status(world):
    if world.active_conflicts:
        log(f"  Active conflicts ({len(world.active_conflicts)}):")
        for c in world.active_conflicts:
            log(f"    {c.attacker.name} ({int(c.attacker.military_strength):,}) vs {c.defender.name} [{c.contested_territory}] (garrison {int(c._defender_garrison):,} / total {int(c.defender.military_strength):,}) - Month {c.duration_days}")

    if world.current_day % 12 == 0:
        log(f"\n  Top 5 countries by military strength:")
        top = sorted(world.countries, key=lambda c: c.military_strength, reverse=True)[:5]
        for c in top:
            log(f"    {c.name}: {int(c.military_strength):,} troops, economy {int(c.economy):,}, tech {c.tech_level:.1f}")

        if world.alliances:
            log(f"\n  Active alliances ({len(world.alliances)}):")
            for a in world.alliances:
                log(f"    {a.name}")
        log("")

def apply_events(world, events):
    non_combat_events = [e for e in events if e.type not in ("invasion", "war")]
    for country in world.countries:
        if random.random() < 0.04:
            event = random.choice(non_combat_events)

            # Each event rolls its own severity: 60%–140% of the base impact
            severity = random.uniform(0.6, 1.4)
            econ_hit = event.economy_impact * severity
            mil_hit  = event.military_impact * severity
            # Population impacts are dampened — events disrupt growth, not kill millions.
            # Wars and disasters handle real casualties separately.
            pop_hit  = event.population_impact * severity * 0.25

            country.economy = max(0, int(country.economy * (1 + econ_hit)))
            country.military_strength = max(0, int(country.military_strength * (1 + mil_hit)))
            country.military_strength = min(country.military_strength, country.military_cap)
            country.population = max(1, int(country.population * (1 + pop_hit)))

            flavor = random.choice(event.flavor) if event.flavor else ""

            impacts = []
            if econ_hit != 0:
                sign = "+" if econ_hit > 0 else ""
                impacts.append(f"Economy {sign}{econ_hit * 100:.0f}%")
            if mil_hit != 0:
                sign = "+" if mil_hit > 0 else ""
                impacts.append(f"Military {sign}{mil_hit * 100:.0f}%")
            if pop_hit != 0:
                sign = "+" if pop_hit > 0 else ""
                impacts.append(f"Population {sign}{pop_hit * 100:.0f}%")
            impact_str = f" [{', '.join(impacts)}]" if impacts else ""

            log(f"  [EVENT] {country.name} - {event.name}: {flavor}{impact_str}")

def simulate_day(world, events):
    apply_events(world, events)

    # War exhaustion decays over time — nations gradually recover their appetite for conflict
    for country in world.countries:
        if country.war_exhaustion > 0:
            country.war_exhaustion = max(0.0, country.war_exhaustion - 0.04)

    # Natural population growth (annual rate applied monthly)
    # Nations at war skip growth — civilian casualties in Conflict handle their population
    at_war_countries = {c.attacker for c in world.active_conflicts} | {c.defender for c in world.active_conflicts}
    for country in world.countries:
        if country not in at_war_countries:
            country.population = int(country.population * (1 + country.population_growth / 12))

    # Military recruitment: nations build toward a target force size each month
    for country in world.countries:
        if country in at_war_countries:
            # Wartime mobilisation: draft toward a large fraction of theoretical cap
            target = int(country.military_cap * WARTIME_ARMY_TARGET)
        else:
            # Peacetime: standing army scales with global tension
            # At risk=0: 1.2% of pop. At risk=0.70: ~4% of pop.
            tension_target = PEACETIME_ARMY_BASE + world.risk * PEACETIME_ARMY_SCALE
            target = int(country.population * tension_target)
        target = min(target, country.military_cap)
        if country.military_strength < target:
            recruit = max(1, int((target - country.military_strength) * RECRUITMENT_RATE))
            country.military_strength = min(country.military_strength + recruit, country.military_cap)

    # Tech growth: each month, nations edge toward their GDP-per-capita tech target.
    # Logarithmic and uncapped — a wealthy empire keeps advancing indefinitely.
    # Tech only ever improves; annexing poorer nations never regresses your R&D.
    for country in world.countries:
        gdp_per_capita = country.economy / max(country.population, 1)
        target_tech = 1.0 + 2.0 * math.log10(1 + gdp_per_capita / 500)
        if target_tech > country.tech_level:
            country.tech_level = round(country.tech_level + (target_tech - country.tech_level) * 0.03, 2)

    for conflict in list(world.active_conflicts):
        conflict.simulate_day(len(world.countries), world.endgame_nuke_threshold)
        # Drain any nuclear strikes that fired this tick into the world queue
        world.pending_strikes.extend(conflict.pending_strikes)
        conflict.pending_strikes.clear()
        if conflict.is_over:
            world.active_conflicts.remove(conflict)
            winner, loser = conflict.winner, conflict.loser

            # War exhaustion: both sides become less likely to start new conflicts.
            # Scales with duration — longer wars leave nations more drained.
            exhaustion = min(0.75, 0.10 + conflict.duration_days * 0.008)
            if winner:
                winner.war_exhaustion = min(1.0, winner.war_exhaustion + exhaustion * 0.6)
            if loser:
                loser.war_exhaustion  = min(1.0, loser.war_exhaustion  + exhaustion)

            if conflict.peace_deal == 'merger':
                # Negotiated union — both names blend, full resource transfer
                alliance = get_alliance(winner, world)
                merge_countries(winner, loser, world)
                if alliance and alliance in world.alliances:
                    world.alliances.remove(alliance)

            elif conflict.peace_deal == 'annexation':
                # Unconditional surrender — winner's name survives, full resources
                annexe(winner, loser, world)

            else:
                # Military defeat — if winner refused a peace offer, pyrrhic penalty applies
                if conflict.pyrrhic:
                    loser.economy    = int(loser.economy    * PYRRHIC_RATIO)
                    loser.population = max(1, int(loser.population * PYRRHIC_RATIO))
                    loser.nukes      = int(loser.nukes      * PYRRHIC_RATIO)
                    flavor = random.choice(_PEACE_PYRRHIC_FLAVORS).format(winner=winner.name, loser=loser.name)
                    log(f"  [PEACE] {flavor}")
                annexe(winner, loser, world)

    for country in list(world.countries):
        targets = get_targets(country, world)
        if not targets:
            continue

        target = random.choice(targets)

        already_at_war = any(
            (c.attacker == country or c.defender == country or
             c.attacker == target or c.defender == target)
            for c in world.active_conflicts
        )
        if already_at_war:
            continue

        strength_ratio = country.military_strength / max(target.military_strength, 1)
        base_probability = next((e.base_probability for e in events if e.type == "invasion"), 0.01)

        # Nuclear deterrence: each warhead tier halves willingness to attack
        nuclear_deterrence = 1.0 / (1.0 + 0.5 * (target.nukes / 100) ** 0.5) if target.nukes > 0 else 1.0
        attack_chance = base_probability * strength_ratio * world.risk * nuclear_deterrence * (1.0 - country.war_exhaustion)

        if random.random() < attack_chance:
            if strength_ratio >= INVASION_THRESHOLD:
                # The underdog gets a chance to resist based on their tech advantage
                tech_factor   = target.tech_level / max(country.tech_level, 0.1)
                resist_chance = min(0.80, 0.35 * tech_factor)
                if random.random() < resist_chance:
                    if tech_factor > 1.1:
                        flavor = random.choice(_WAR_TECH_DEFIANCE_FLAVORS).format(defender=target.name, attacker=country.name)
                    else:
                        flavor = random.choice(_WAR_BRAVE_RESISTANCE_FLAVORS).format(defender=target.name, attacker=country.name)
                    log(f"  >> {flavor}")
                    conflict = Conflict(country, target)
                    world.active_conflicts.append(conflict)
                    trigger_alliance_support(country, target, world)
                else:
                    flavor = random.choice(_WAR_INSTANT_FLAVORS).format(attacker=country.name, defender=target.name)
                    log(f"  >> {flavor}")
                    annexe(country, target, world)
            else:
                conflict = Conflict(country, target)
                world.active_conflicts.append(conflict)
                flavor = random.choice(_WAR_DECLARATION_FLAVORS).format(attacker=country.name, defender=target.name)
                log(f"  >> {flavor}")
                trigger_alliance_support(country, target, world)

    # Nuclear proliferation: gradual uranium enrichment gated on tech + world tension
    if world.risk >= NUKE_RISK_THRESHOLD:
        for country in list(world.countries):
            # Skip superpowers with existing massive arsenals (Russia/USA tier)
            if country.nukes >= NUKE_MAX_STOCKPILE:
                continue
            if country.tech_level < NUKE_TECH_THRESHOLD:
                continue
            # Accumulate enriched uranium; rate scales with tech level
            rate_mult = min(URANIUM_RATE_MAX_MULT, country.tech_level / NUKE_TECH_THRESHOLD)
            prev_uranium = country.uranium
            country.uranium += URANIUM_RATE_BASE * rate_mult
            # Log when enrichment first starts (only for non-nuclear nations, transition from 0)
            if prev_uranium == 0.0 and country.nukes == 0:
                flavor = random.choice(_NUCLEAR_ENRICHMENT_FLAVORS).format(country=country.name)
                log(f"  [NUCLEAR] \u2622 {flavor}")
            # Convert accumulated uranium into warheads
            while country.uranium >= URANIUM_PER_NUKE:
                country.uranium -= URANIUM_PER_NUKE
                country.nukes += 1
                if country.nukes == 1:
                    flavor = random.choice(_NUCLEAR_PROLIFERATION_FLAVORS).format(country=country.name)
                    log(f"  [NUCLEAR] \u2622 {flavor}")
                elif country.nukes in (10, 25, 50, 100, 250, 500, 1000, 2000):
                    flavor = random.choice(_NUCLEAR_MILESTONE_FLAVORS).format(country=country.name, n=country.nukes)
                    log(f"  [NUCLEAR] \u2622 {flavor}")

    decay_alliances(world)
    form_alliances(world)
    check_final_war(world)

def _update_risk(current_day, current_risk):
    if current_day <= PEACE_MONTHS:
        return 0.0
    if current_day <= PEACE_MONTHS + RAMP_MONTHS:
        t = (current_day - PEACE_MONTHS) / RAMP_MONTHS
        return round(BASE_RISK * t, 4)
    # Post-ramp: risk creeps up slowly, representing mounting global tension
    extra = (current_day - PEACE_MONTHS - RAMP_MONTHS) * RISK_ESCALATION
    return min(MAX_RISK, round(BASE_RISK + extra, 4))

def main():
    log("Loading world data...")
    countries = load_countries(start_year=START_YEAR)
    events = load_events()

    world = World(
        stability=1.0,
        risk=0.0,
        countries=countries
    )

    log(f"World initialized with {len(world.countries)} countries.")
    log(f"Simulation start date: {START_DATE.strftime('%B %d, %Y')}")
    log("Starting simulation...\n")

    last_conflict_month = PEACE_MONTHS  # tracks when a conflict last broke out

    running = True
    while running:
        world.current_day += 1
        date_str = current_date(world).strftime("%B %d, %Y")

        world.risk = _update_risk(world.current_day, world.risk)

        if world.current_day == PEACE_MONTHS + 1:
            log(f"  [WORLD] {random.choice(_WORLD_PEACE_ENDS_FLAVORS)}")
        elif world.current_day == PEACE_MONTHS + RAMP_MONTHS + 1:
            log(f"  [WORLD] {random.choice(_WORLD_TENSIONS_PEAK_FLAVORS)}")

        conflicts_before = len(world.active_conflicts)
        simulate_day(world, events)
        if len(world.active_conflicts) > conflicts_before:
            last_conflict_month = world.current_day

        # Stalemate breaker: if no new war has started in world.stalemate_months, force one
        if (world.risk >= BASE_RISK
                and not world.active_conflicts
                and len(world.countries) > 1
                and world.current_day - last_conflict_month >= world.stalemate_months):
            candidates = sorted(world.countries, key=lambda c: c.military_strength, reverse=True)
            aggressor = candidates[0]
            target    = random.choice(candidates[1:])
            flavor = random.choice(_STALEMATE_FLAVORS).format(aggressor=aggressor.name, target=target.name)
            log(f"  [WORLD] {flavor}")
            world.active_conflicts.append(Conflict(aggressor, target))
            trigger_alliance_support(aggressor, target, world)
            last_conflict_month = world.current_day

        log(f"{date_str} - {len(world.countries)} countries remaining")
        print_status(world)

        time.sleep(sleep_time)

        if len(world.countries) <= 1:
            date_str = current_date(world).strftime("%B %d, %Y")
            log(f"\nSimulation over! {world.countries[0].name} conquered the world on {date_str}!")
            log(f"Total simulation time: {world.current_day} months ({world.current_day // 12} years, {world.current_day % 12} months)")
            running = False

if __name__ == "__main__":
    main()
