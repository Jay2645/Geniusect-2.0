#!/usr/bin/env python3

from src.ai.ia import make_best_action, make_best_switch, make_best_move, make_best_order

from src.io_process import senders
from src.io_process.json_loader import request_loader

from src.game_engine.battle import Battle
from src.helpers import player_id_to_index
from src.ui.user_interface import UserInterface

class Match:
    """
    This represents an actual match window in Pokemon Showdown.
    This references the Battle instance, the current tier 
    (OU, UU, Random Battle, etc.), how much time is left on this
    current turn, etc.
    
    This doesn't handle anything on-cartridge in a Pokemon game;
    that should all be handled by the Battle class. This only
    handles Smogon/Showdown-specific rules that aren't on a cartidge.
    """

    def __init__(self, match_id):
        self.battle_id = match_id
        self.battle = Battle(self, {"id":match_id, "name":match_id})
        self.rules = []
        self.sides = [
            {
                "name":"",
                "team_size":0,
                "showdown_id":"",
                "is_bot":False
            },
            {
                "name":"",
                "team_size":0,
                "showdown_id":"",
                "is_bot":False
            }
        ]
        self.gen = 0
        self.turn = 0
        self.turn_timer = 0
        self.tier = ""
        self.match_window = None
        print("Created match.")
        
    def set_player_name(self, player_id, player_name):
        from src.io_process.showdown import Showdown
        login = Showdown()
        is_us = login.username.lower() == player_name.lower()

        player_index = player_id_to_index(player_id)
        self.sides[player_index]['name'] = player_name
        self.sides[player_index]['showdown_id'] = player_id
        self.sides[player_index]['is_bot'] = is_us
        self.sides[player_index]['index'] = player_id

        self.battle.update_player(self.sides[player_index], player_index)

    def set_team_size(self, player_id, team_size):
        player_index = player_id_to_index(player_id)
        self.sides[player_index]['team_size'] = team_size

        self.battle.update_player(self.sides[player_index], player_index)
        if self.match_window != None:
            self.match_window.update_teams(self.battle.teams)

    def set_title(self, title):
        self.battle.name = title
        self.battle.full_name = self.battle.name + ": " + self.battle.id

    def set_generation(self, generation):
        self.gen = int(generation)
        self.battle.gen = self.gen

    def set_tier(self, tier):
        self.tier = tier

    def add_rule(self, rule):
        self.rules.append(rule)

    async def recieved_request(self, request):
        if request == "":
            return
        team_details = request_loader(request, self.battle)
        self.battle.update_us(team_details)
        if self.battle.force_switch:
            from src.io_process.showdown import Showdown
            login = Showdown()
            websocket = login.websocket
            await self.make_switch(websocket)
        elif self.battle.is_trapped:
            from src.io_process.showdown import Showdown
            login = Showdown()
            websocket = login.websocket
            await self.make_move(websocket)

    async def new_turn(self, turn_number):
        self.turn = int(turn_number)
        print("Beginning turn " + str(turn_number))

        from src.io_process.showdown import Showdown
        login = Showdown()
        websocket = login.websocket
        await self.make_action(websocket)

    async def new_player_joined(self, websocket, username):
        await senders.sendmessage(websocket, self.battle_id, "Hi, " + username + "! I'm a bot! I'm probably going to crash and forfeit at some point, so be nice!")

    def set_turn_timer(self, turn_amount):
        try:
            self.turn_timer = int(turn_amount)
        except ValueError:
            pass

    async def make_team_order(self, websocket):
        """
        Call function to correctly choose the first pokemon to send.
        :param websocket: Websocket stream.
        """
        print("Making team order")

        order = "".join([str(x[0]) for x in make_best_order(self, self.id.split('-')[1])])
        await senders.sendmessage(websocket, self.battle.id, "/team " + order + "|" + str(self.battle.turn))

    async def make_move(self, websocket, best_move=None):
        """
        Call function to send move and use the sendmove sender.
        :param websocket: Websocket stream.
        :param best_move: [int, int] : [id of best move, value].
        """
        if self.battle.force_switch:
            await self.make_switch(websocket)
            return

        if not best_move:
            best_move = make_best_move(self.battle)

        pokemon = self.battle.teams[player_id_to_index(self.battle.player_id)].active()
        plan_text = ""
        if best_move[1] == 1024:
            plan_text = "Using locked-in move!"
        else:
            plan_text = "Using move " + str(pokemon.moves[best_move[0] - 1].name)

        print(plan_text)
        ui = UserInterface()
        ui.update_plan(self.battle_id, plan_text)

        best_move_string = str(best_move[0])
        if "canMegaEvo" in self.battle.current_pkm[0]:
            best_move_string = str(best_move[0]) + " mega"
        await senders.sendmove(websocket, self.battle_id, best_move_string, self.battle.turn)

    async def make_switch(self, websocket, best_switch = None, force_switch = False):
        """
        Call function to send switch and use the sendswitch sender.
        :param websocket: Websocket stream.
        :param best_switch: int, id of pokemon to switch.
        """
        if self.battle.is_trapped:
            await self.make_move(websocket)
            return

        if not best_switch:
            best_switch = make_best_switch(self.battle, force_switch)[0]

        plan_text = ""

        if best_switch >= 0:
            plan_text = "Making a switch to " + self.battle.teams[player_id_to_index(self.battle.player_id)].pokemon[best_switch - 1].name
        else:
            raise RuntimeError("Could not determine a Pokemon to switch to.")
        
        print(plan_text)

        from src.ui.user_interface import UserInterface
        ui = UserInterface()
        ui.update_plan(self.battle_id, plan_text)

        await senders.sendswitch(websocket, self.battle_id, best_switch, self.battle.turn)

    async def make_action(self, websocket):
        """
        Launch best action chooser and call corresponding functions.
        :param websocket: Websocket stream.
        """
        action = make_best_action(self.battle)
        if action[0] == "move":
            await self.make_move(websocket, action[1:])
        if action[0] == "switch":
            await self.make_switch(websocket, action[1])


    async def cant_take_action(self, disabled_action):
        self.battle.cant_take_action(disabled_action)
        await self.battle.new_turn(self.turn)

    async def must_make_move(self, websocket):
        await self.battle.make_move(websocket)

    def open_match_window(self):
        ui = UserInterface()
        ui.make_new_match(self)

    async def game_is_over(self, websocket, winner_name):
        from src.io_process.showdown import Showdown
        login = Showdown()
        if winner_name == login.username:
            login.wins += 1
        else:
            login.losses += 1

        await senders.sendmessage(websocket, self.battle_id, "Well played! So far this session, my win:loss ratio has been: " + str(login.wins) + ":" + str(login.losses) + ".")
        await login.game_over(self)