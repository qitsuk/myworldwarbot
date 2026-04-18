class Alliance:
    def __init__(self, members, formed_day=0):
        self.members = list(members)
        self.formed_day = formed_day  # simulation day when the alliance was created

    @property
    def name(self):
        return " & ".join(c.name for c in self.members)

    def has_member(self, country):
        return country in self.members

    def get_allies(self, country):
        return [c for c in self.members if c != country]

    def remove_member(self, country):
        if country in self.members:
            self.members.remove(country)

    def __repr__(self):
        return f"Alliance({self.name})"
