from src.game_engine.battle import Battle
from src.helpers import player_id_to_index

class AI():
    def __init__(self):
        pass

    def make_best_order(self, battle : Battle, form=None):
        team = battle.teams[player_id_to_index(battle.player_id)]
        ordered_team = []
        for i, pokemon in enumerate(team.pokemon):
            ordered_team.append([i + 1, 0])
        return ordered_team

    def make_best_action(self, battle : Battle, must_switch : bool = False, must_move : bool = False):
        """
        Choose best action to do each turn.
        Select best action of bot and enemy pokemon, then best pokemon to switch. And finally, chose if it worth or not to
        switch.
        :param battle: Battle object, current battle.
        :return: (Index of move in pokemon (["move"|"switch"], Integer, [-1, 6]))
        """
        raise NotImplementedError()