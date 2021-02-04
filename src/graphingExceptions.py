# Error 301
class StatNotTrackedError(Exception):
    def __init__(self, statName, playerName):
        self.stat = statName
        self.player = playerName


# Error 302
class NoPlayersSelected(Exception):
    pass


# Error 303
class IncompleteRatioStatError(Exception):
    def __init__(self, statName, playerName, date):
        self.stat = statName
        self.player = playerName
        self.date = date

