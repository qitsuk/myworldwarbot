class World:
    def __init__(self, stability, risk, countries=None, current_day=0):
        self.countries = countries if countries is not None else []
        self.stability = stability
        self.risk = risk
        self.current_day = current_day
        self.active_conflicts = []