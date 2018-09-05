import re
import json
from json import JSONDecodeError

from src.ai.ia import make_best_action, make_best_switch, make_best_move, make_best_order
from src.game_engine.pokemon import Pokemon, Status
from src.game_engine.team import Team
from src.io_process import senders
from src.errors import ShowdownError
from src.helpers import player_id_to_index, get_enemy_id_from_player_id


class Battle:
    """
    Battle class.
    Unique for each battle.
    Handle everything concerning it.
    """
    def __init__(self, battle_id):
        """
        init Battle method.
        :param battle_id: String, battle_id of battle.
        """
        self.teams = [Team(), Team()]
        self.current_pkm = None
        self.turn = 0
        self.battle_id = battle_id
        self.player_id = ""
        print("Battle started")
        
    async def update_us(self, team_details):
        from src.ui.user_interface import UserInterface
        from src.io_process.showdown import Showdown

        player_index = player_id_to_index(self.player_id)
        self.teams[player_index] = team_details['team']
        self.current_pkm = team_details['active']
        self.turn = team_details['turn']

        ui = UserInterface()
        ui.update_team_ui(self.battle_id, self.teams)

        if team_details['force_switch']:
            login = Showdown()
            await self.make_switch(login.websocket, None, True)
        elif team_details['trapped']:
            login = Showdown()
            await self.make_move(login.websocket)

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
            pkm = Pokemon(pkm_name, condition, True, level)
            pkm.load_unknown()
            self.teams[enemy_index].add(pkm)
        else:
            # This is a Pokemon we already know about
            for pkm in self.teams[enemy_index].pokemon:
                # Mark this Pokemon as active and the others as inactive
                if pkm.name.lower() == pkm_name.lower():
                    pkm.active = True
                else:
                    pkm.active = False
        
        ui = UserInterface()
        ui.update_team_ui(self.battle_id, self.teams)

    def update_player(self, player_data, player_index):
        if player_data['is_bot']:
            self.player_id = player_data['showdown_id']

    def get_bot_team(self):
        return self.teams[0] if self.teams[0].is_bot else self.teams[1]

    def get_active_pokemon(self):
        our_team = self.get_bot_team()
        return our_team.active()

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

    async def new_turn(self, turn_number):
        print("Beginning turn " + str(turn_number))
        from src.io_process.showdown import Showdown
        login = Showdown()
        websocket = login.websocket
        await self.make_action(websocket)

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
    
    async def make_team_order(self, websocket):
        """
        Call function to correctly choose the first pokemon to send.
        :param websocket: Websocket stream.
        """
        print("Making team order")

        order = "".join([str(x[0]) for x in make_best_order(self, self.battle_id.split('-')[1])])
        await senders.sendmessage(websocket, self.battle_id, "/team " + order + "|" + str(self.turn))

    async def make_move(self, websocket, best_move=None):
        """
        Call function to send move and use the sendmove sender.
        :param websocket: Websocket stream.
        :param best_move: [int, int] : [id of best move, value].
        """
        if not best_move:
            best_move = make_best_move(self)

        pokemon = self.teams[player_id_to_index(self.player_id)].active()
        plan_text = ""
        if best_move[1] == 1024:
            plan_text = "Using locked-in move!"
        else:
            plan_text = "Using move " + str(pokemon.moves[best_move[0] - 1].name)

        print(plan_text)
        from src.ui.user_interface import UserInterface
        ui = UserInterface()
        ui.update_plan(self.battle_id, plan_text)

        best_move_string = str(best_move[0])
        if "canMegaEvo" in self.current_pkm[0]:
            best_move_string = str(best_move[0]) + " mega"
        await senders.sendmove(websocket, self.battle_id, best_move_string, self.turn)

    async def make_switch(self, websocket, best_switch = None, force_switch = False):
        """
        Call function to send switch and use the sendswitch sender.
        :param websocket: Websocket stream.
        :param best_switch: int, id of pokemon to switch.
        """
        if not best_switch:
            best_switch = make_best_switch(self, force_switch)[0]

        plan_text = ""

        if best_switch >= 0:
            plan_text = "Making a switch to " + self.teams[player_id_to_index(self.player_id)].pokemon[best_switch - 1].name
        else:
            raise RuntimeError("Could not determine a Pokemon to switch to.")
        print(plan_text)
        from src.ui.user_interface import UserInterface
        ui = UserInterface()
        ui.update_plan(self.battle_id, plan_text)

        await senders.sendswitch(websocket, self.battle_id, best_switch, self.turn)

    async def make_action(self, websocket):
        """
        Launch best action chooser and call corresponding functions.
        :param websocket: Websocket stream.
        """
        action = make_best_action(self)
        if action[0] == "move":
            await self.make_move(websocket, action[1:])
        if action[0] == "switch":
            await self.make_switch(websocket, action[1])
