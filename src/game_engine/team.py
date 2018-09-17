#!/usr/bin/env python3

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

    def active(self):
        """
        Return active pokemon of Team
        :return: Pokemon
        """
        for pkm in self.pokemon:
            if pkm.active:
                return pkm
        return None

    def add(self, pokemon):
        """
        Add pokemon to self.pokemon array. Exit and print error message if Team is full (6 pokemon)
        :param pokemon: Pokemon
        """
        if len(self.pokemon) < 6:
            pokemon.team = self
            self.pokemon.append(pokemon)
        else:
            raise IndexError("Failed to add " + pokemon.species + " : there is yet six pokemon in team :\n" + str(self))

    def remove(self, pkm_name):
        """
        Remove pokemon from self.pokemon array. Exit and print error message if pkm_name not present in self.pokemon
        :param pkm_name: Name of pokemon
        """
        for i, pkm in enumerate(self.pokemon):
            if pkm_name in pkm.species.lower():
                if "mega" not in pkm.species.lower():
                    del self.pokemon[i]
                return
        raise NameError("Unable to remove " + pkm_name + " from team :\n" + str(self))

    def create_team_object(self):
        from src.io_process import showdown
        team_object = {
            "name": "Bot" if self.is_bot else "Enemy",
            "avatar": showdown.avatar if self.is_bot else 1,
            "team": []
        }

        for pkm in self.pokemon:
            team_object["team"].append(pkm.get_set_object())

        return team_object

    def __contains__(self, pkm_name: str):
        return any(pkm.species == pkm_name for pkm in self.pokemon)
        # for pkm in self.pokemon:
        #     if pkm.species == pkm_name:
        #         return True
        # return False

    def __repr__(self):
        return ', '.join([pkm.species for pkm in self.pokemon])

    def __str__(self):
        return '\n============\n'.join([str(pkm) for pkm in self.pokemon])

