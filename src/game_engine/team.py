#!/usr/bin/env python3

class Team:
    """
    Team class.
    Contain pokemon list.
    """
    def __init__(self, *pkms):
        """
        init Team method
        :param pkms: Array of Pokemon. Can be empty, Cannot contain more than six pokemon.
        """
        self.pokemons = []
        for pkm in pkms:
            self.add(pkm)
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
        for pkm in self.pokemons:
            if pkm.active:
                return pkm
        return None

    def add(self, pokemon):
        """
        Add pokemon to self.pokemons array. Exit and print error message if Team is full (6 pokemons)
        :param pokemon: Pokemon
        """
        if len(self.pokemons) < 6:
            pokemon.team = self
            self.pokemons.append(pokemon)
        else:
            raise IndexError("Failed to add " + pokemon.name + " : there is yet six pokemon in team :\n" + str(self))

    def remove(self, pkm_name):
        """
        Remove pokemon from self.pokemons array. Exit and print error message if pkm_name not present in self.pokemons
        :param pkm_name: Name of pokemon
        """
        for i, pkm in enumerate(self.pokemons):
            if pkm_name in pkm.name.lower():
                if "mega" not in pkm.name.lower():
                    del self.pokemons[i]
                return
        raise NameError("Unable to remove " + pkm_name + " from team :\n" + str(self))

    def __contains__(self, pkm_name: str):
        return any(pkm.name == pkm_name for pkm in self.pokemons)
        # for pkm in self.pokemons:
        #     if pkm.name == pkm_name:
        #         return True
        # return False

    def __repr__(self):
        return ', '.join([pkm.name for pkm in self.pokemons])

    def __str__(self):
        return '\n============\n'.join([str(pkm) for pkm in self.pokemons])

