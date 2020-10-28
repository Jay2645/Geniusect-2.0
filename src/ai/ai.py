from src.io_process.match import Match
from src.io_process.senders import Action

class AI():
    def __init__(self):
        pass

    def make_best_action(self, match : Match) -> Action:
        """
        Choose best action to do each turn.
        Select best action of bot and enemy pokemon, then best pokemon to switch. And finally, chose if it worth or not to
        switch.
        :param battle: Battle object, current battle.
        :return: (Index of move in pokemon (["move"|"switch"], Integer, [-1, 6]))
        """
        raise NotImplementedError()