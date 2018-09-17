#!/usr/bin/env python3

import re
import random

from node_vm2 import NodeVM, VMError

from src.game_engine.pokemon import Pokemon
from src.game_engine.game_calcs import Status
from src.game_engine.team import Team
from src.errors import ShowdownError
from src.game_engine.effects import Entity
from src.helpers import player_id_to_index, get_enemy_id_from_player_id, index_to_player_id

class Battle(Entity):
    """
    Battle class. This holds references to both teams.
    It also holds references to things which affect both teams, like weather effects
    and what turn it is.
    """
    def __init__(self, match, battle_object):
        """
        init Battle method.
        :param battle_object: Dict, containing the Entity JSON for this battle.
        """
        super().__init__(battle_object)

        self.match = match
        self.teams = [Team(self), Team(self)]
        self.current_pkm = None
        self.turn = 0
        self.player_id = ""
        self.pseudo_weather = []
        self.force_switch = False
        self.is_trapped = False
        self.format = battle_object["format"]

        self.vm = NodeVM()
        with open("src/game_engine/js/battlehelper.js", "r", encoding='utf-8') as battlehelper:
            jscode = battlehelper.read()
        self.battle_module = self.vm.code(jscode, "src/game_engine/js/battlehelper.js", console = "redirect", require = {"external": True, "builtin": ["*"]})
        self.battle_json = {}

    def start_battle(self):
        random.seed()
        battle_options = {"format":self.format, "seed":[random.randint(0, 65535), random.randint(0, 65535), random.randint(0, 65535), random.randint(0, 65535)]}
        battle_json = self.battle_module.call_member("createBattle", battle_options)
        
        self.__update_battle_team("p1", self.teams[0])
        self.__update_battle_team("p2", self.teams[1])
        print("Battle started in format " + self.format)
        
    def update_us(self, team_details):
        from src.ui.user_interface import UserInterface
        from src.io_process.showdown import Showdown

        player_index = player_id_to_index(self.player_id)
        self.teams[player_index] = team_details['team']
        self.current_pkm = team_details['active']
        self.turn = team_details['turn']
        
        self.force_switch = team_details['force_switch']
        self.is_trapped = team_details['trapped']

        ui = UserInterface()
        ui.update_team_ui(self.id, self.teams)
        
        self.__update_battle_team(self.player_id, self.teams[player_index])

    def __update_battle_team(self, player_index, player_team):
        team_object = player_team.create_team_object()
        if len(team_object['team']) == 0:
            print(team_object['name'] + " had an empty team.")
            return

        print(team_object)

        self.battle_module.call_member("updateBattleTeam", player_index, team_object)
        
        self.update_battle_json()

    def __update_battle_json(self, battle_json):
        from json import loads, JSONDecodeError
        try:
            self.battle_json = loads(battle_json)
            if self.battle_json == None:
                self.battle_json = {}
        except JSONDecodeError:
            self.battle_json = {}

    def update_enemy(self, pkm_name, level, condition):
        """
        On first turn, and each time enemy switch, update enemy team and enemy current pokemon.
        :param pkm_name: Pokemon's name
        :param level: int, Pokemon's level
        :param condition: str current_hp/total_hp. /100 if enemy pkm.
        """
        from src.ui.user_interface import UserInterface
        enemy_index = get_enemy_id_from_player_id(self.player_id)
        if "-mega" in pkm_name.lower():
            self.teams[enemy_index].remove(pkm_name.lower().split("-mega")[0])
        if "-*" in pkm_name.lower():
            pkm_name = re.sub(r"(.+)-\*", r"\1", pkm_name)
        elif re.compile(r".+-.*").search(pkm_name.lower()):
            try:
                self.teams[enemy_index].remove(re.sub(r"(.+)-.+", r"\1", pkm_name))
            except NameError:
                pass

        # Check to see if the Pokemon is in the enemy team
        if pkm_name not in self.teams[enemy_index]:
            # This is a new Pokemon we're seeing
            # Mark all enemy Pokemon as inactive
            for pkm in self.teams[enemy_index].pokemon:
                pkm.active = False
            # Load this new Pokemon with an unknown set of data
            pkm = Pokemon(self, pkm_name, condition, True, level)
            pkm.load_unknown()
            self.teams[enemy_index].add(pkm)
        else:
            # This is a Pokemon we already know about
            for pkm in self.teams[enemy_index].pokemon:
                # Mark this Pokemon as active and the others as inactive
                if pkm.species.lower() == pkm_name.lower():
                    pkm.active = True
                else:
                    pkm.active = False
        
        ui = UserInterface()
        ui.update_team_ui(self.id, self.teams)

        enemy_id = index_to_player_id(enemy_index)
        self.__update_battle_team(enemy_id, self.teams[enemy_index])

    def update_player(self, player_data, player_index):
        if player_data['is_bot']:
            self.player_id = player_data['showdown_id']

    def get_bot_team(self):
        return self.teams[0] if self.teams[0].is_bot else self.teams[1]

    def get_active_pokemon(self):
        our_team = self.get_bot_team()
        return our_team.active()

    def update_battle_json(self):
        battle_json = self.battle_module.call_member("getBattleJSON")
        self.__update_battle_json(battle_json)
        return self.battle_json

    @staticmethod
    def update_status(pokemon, status: str = ""):
        """
        Update status problem.
        :param pokemon: Pokemon.
        :param status: String.
        """
        if status == "tox":
            pokemon.status = Status.toxic
        elif status == "brn":
            pokemon.status = Status.burned
        elif status == "par":
            pokemon.status = Status.paralyzed
        elif status == "psn":
            pokemon.status = Status.poisoned
        elif status == "slp":
            pokemon.status = Status.asleep
        else:
            pokemon.status = Status.healthy

    @staticmethod
    def set_buff(pokemon, stat, quantity):
        """
        Set buff to pokemon
        :param pokemon: Pokemon
        :param stat: str (len = 3)
        :param quantity: int [-6, 6]
        """
        modifs = {"-6": 1/4, "-5": 2/7, "-4": 1/3, "-3": 2/5, "-2": 1/2, "-1": 2/3, "0": 1, "1": 3/2, "2": 2, "3": 5/2,
                  "4": 3, "5": 7/2, "6": 4}
        buff = pokemon.buff[stat][0] + quantity
        if -6 <= buff <= 6:
            pokemon.buff[stat] = [buff, modifs[str(buff)]]

    def cant_take_action(self, disabled_action):
        active_pkm = self.teams[player_id_to_index(self.player_id)].active()
        for move in active_pkm.moves:
            if move.id == disabled_action:
                move.disabled = True
                return
        raise ShowdownError("Can't do " + disabled_action)
    
    def battle_over(self):
        try:
            self.vm.destroy()
        except VMError:
            pass
        self.vm = None
        self.battle_module = None