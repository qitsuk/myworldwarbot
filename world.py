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
        self.pending_strikes = []    # [(launcher_name, target_name)] — cleared by server after broadcast