#!/usr/bin/env python3

from src.game_engine.pokemon import Pokemon

class Team:
    """
    Team class.
    Contain pokemon list.
    """
    def __init__(self, battle):
        """
        init Team method
        """
        self.is_bot = False
        self.battle = battle
        self.pokemon = []
        self.entry_hazards = {
            "stealth_rock": 0,
            "spikes": 0,
            "toxic_spikes": 0,
            "sticky_web": 0
        }
        self.reflect = False
        self.light_screen = False

    def active(self) -> Pokemon or None:
        """
        Return active pokemon of Team
        :return: Pokemon
        """
        for pkm in self.pokemon:
            if pkm.active:
                return pkm
        return None

    def add(self, pokemon : Pokemon):
        """
        Add pokemon to self.pokemon array. Exit and print error message if Team is full (6 pokemon)
        :param pokemon: Pokemon
        """
        if len(self.pokemon) < 6:
            pokemon.team = self
            self.pokemon.append(pokemon)
        else:
            raise IndexError("Failed to add " + pokemon.name + " : there is six pokemon in team :\n" + str(self))

    def remove(self, pkm_name : str):
        """
        Remove pokemon from self.pokemon array. Exit and print error message if pkm_name not present in self.pokemon
        :param pkm_name: Name of pokemon
        """
        for i, pkm in enumerate(self.pokemon):
            if pkm_name in pkm.name.lower():
                if "mega" not in pkm.name.lower():
                    del self.pokemon[i]
                return
        raise NameError("Unable to remove " + pkm_name + " from team :\n" + str(self))

    def __contains__(self, pkm_name: str):
        return any(pkm.name == pkm_name for pkm in self.pokemon)
        # for pkm in self.pokemon:
        #     if pkm.name == pkm_name:
        #         return True
        # return False

    def __repr__(self):
        return ', '.join([pkm.name for pkm in self.pokemon])

    def __str__(self):
        return '\n============\n'.join([str(pkm) for pkm in self.pokemon])

