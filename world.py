import random

class World:
    def __init__(self, stability, risk, countries=None, current_day=0):
        self.countries = countries if countries is not None else []
        self.stability = stability
        self.risk = risk
        self.current_day = current_day
        self.active_conflicts = []
        self.alliances = []
        # When surviving nations drop to this count, nuclear trigger chance surges
        self.endgame_nuke_threshold = random.randint(2, 8)
        # How long with no new conflict before the stalemate breaker forces one (varies per run)
        self.stalemate_months = random.randint(18, 48)
        self.pending_strikes = []    # [(launcher_name, target_name, city_name, city_lat, city_lon, used)] — cleared by server
        self.nuked_cities    = []    # [{"lat","lon","city","country","warheads","expires"}] — entries removed when expires < current_day
        self.pending_collateral = [] # [(victim_name, attacker_name, city_name, casualties, lat, lon, warheads)] — processed by simulate_day
        # Cumulative casualty tracking
        self.start_population          = 0   # snapshotted by server after init
        self.total_military_casualties = 0
        self.total_civilian_casualties = 0
        self.total_nukes_used          = 0
