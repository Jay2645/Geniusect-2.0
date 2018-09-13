#!/usr/bin/env python3

from enum import Enum
from math import floor

from src.io_process import json_loader
from src.game_engine.effects import Entity
from src.game_engine.game_calcs import Status, stat_calculation, get_effectiveness, get_immunity


class Pokemon:
    """
    Pokemon class.
    Handle everything corresponding to it.
    """
    def __init__(self, battle, name, condition, active, level):
        """
        Init Pokemon method.
        :param name: name of Pokemon.
        :param condition: ### TODO ###
        :param active: Bool.
        """
        self.name = name
        self.battle = battle
        self.current_health = 0
        self.max_health = 0
        self.condition = condition
        self.active = active
        self.level = int(level)
        self.types = []
        self.item = ""
        self.abilities = []
        self.base_stats = {}
        self.stats = {}
        self.moves = []
        self.substitute = False
        self.buff = {
            "atk": [0, 1],
            "def": [0, 1],
            "spa": [0, 1],
            "spd": [0, 1],
            "spe": [0, 1],
            "accuracy": [0, 1],
            "evasion": [0, 1]
        }
        self.update_health(self.condition)
        self.status = Status.healthy if not self.is_fainted() else Status.fainted

    def load_unknown(self):
        """
        Load every information of pokemon from datafiles and store them
        """
        print("Loading unknown Pokemon " + self.name)
        infos = json_loader.pokemon_from_json(self)
        self.types = infos["types"]
        self.abilities = infos["possibleAbilities"]
        self.base_stats = infos["baseStats"]
        self.moves = infos["possibleMoves"]

    def load_known(self, abilities, item, stats, moves):
        """
        Load ever information of pokemon from datafiles, but use only some of them.
        :param abilities: String. Ability of pokemon.
        :param item: String. Item of pokemon.
        :param stats: Dict. {hp, atk, def, spa, spd, spe}
        :param moves: Array. Not used.
        """
        print("Loading known Pokemon " + self.name)
        infos = json_loader.pokemon_from_json(self)
        self.types = infos["types"]
        self.abilities = abilities
        self.item = item
        self.base_stats = infos["baseStats"]
        self.stats = stats
        self.moves = moves

    def has_type(self, type):
        return type in self.types

    def has_ability(self, ability_id):
        return ability_id in self.abilities

    def get_stat_value(self, stat):
        """
        Gets the actual numerical value of the given stat.
        If the numerical value is unknown, gives a worst-case approximation
        """
        try:
            value = self.stats[stat]
        except KeyError:
            value = stat_calculation(self.base_stats[stat], self.level, 252) 
        return value

    def calculate_stat(self, stat, boost_amount):
        stat_value = self.get_stat_value(stat)

        if stat == 'hp':
            return stat_value

        # Wonder Room swaps defenses before calculating anything else
        if 'wonderroom' in self.battle.pseudo_weather:
            if stat == 'def':
                stat_value = get_stat_value('spd')
            elif stat == 'spd':
                stat_value = get_stat_value('def')

        # Get boosts
        boosts = {}
        boosts[stat] = boost_amount
        boost_amount = boosts[stat]
        boost_table = [1, 1.5, 2, 2.5, 3, 3.5, 4]
        if boost_amount > 6:
            boost_amount = 6
        elif boost_amount < -6:
            boost_amount = -6

        # Multiply the stat value
        if boost_amount >= 0:
            stat_value = floor(stat_value * boost_table[boost_amount])
        else:
            stat_value = floor(stat_value / boost_table[-boost_amount])

        return stat_value

    def run_effectiveness(self, move):
        total_type_mod = 0
        for type in self.types:
            type_mod = get_effectiveness(type, move.type)
            total_type_mod += type_mod
        return total_type_mod

    def run_immunity(self, move_type):
        if self.is_fainted():
            return False
        
        if not get_immunity(move_type, self.types):
            # We are naturally immune
            return False

        return True

    def update_health(self, health_string):
        health = health_string.split('/')
        try:
            self.current_health = int(health[0])
            # Status conditions may follow the max health line
            # We split to strip the status conditions away
            health = health[1].split(' ')
            self.max_health = int(health[0])
        except IndexError:
            pass
        except ValueError:
            self.current_health = 0
            if self.max_health is 0:
                self.max_health = 100

        if self.is_fainted():
            self.status = Status.fainted

    def is_fainted(self):
        return self.condition == "0 fnt"

    def get_hp_percent(self):
        if self.max_health is 0:
            if self.is_fainted():
                return 0
            else:
                return 1
        else:
            return self.current_health / self.max_health

    def cant_use_move(self, move_id):
        for i in range(len(self.moves)):
            if self.moves[i]['id'] is move_id:
                self.moves[i]['disabled'] = True
                return True
        return False

    def buff_affect(self, stat):
        """
        Return buff corresponding to stat
        :param stat: String : ["atk", "def", "spa", "spd", "spe"]
        :return: Float
        """
        return self.buff[stat][1]

    def __repr__(self):
        return str(vars(self))

    def __str__(self):
        output = self.name + " (" + str(self.status) + ")"
        if not self.is_fainted():
            output += "\n" + str(self.current_health) + "/" + str(self.max_health)
        if self.level < 100:
            output += "\nLevel " + str(self.level)
        if self.item is not "" and self.item is not None:
            output += " @ " + str(self.item)
        output += "\nAbilities:" 
        for ability in self.abilities:
            output += "\n"+ability
        return output