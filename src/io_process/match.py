#!/usr/bin/env python3

from src.io_process.senders import sendmessage
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
        self.battle = Battle(match_id)
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

    def set_generation(self, generation):
        self.gen = int(generation)

    def set_tier(self, tier):
        self.tier = tier

    async def recieved_request(self, request):
        if request == "":
            return
        team_details = request_loader(request, self.battle)
        await self.battle.update_us(team_details)

    async def new_turn(self, turn_number):
        self.turn = int(turn_number)
        await self.battle.new_turn(self.turn)

    async def new_player_joined(self, websocket, username):
        await sendmessage(websocket, self.battle_id, "Hi, " + username + "! I'm a bot! I'm probably going to crash and forfeit at some point, so be nice!")

    def set_turn_timer(self, turn_amount):
        try:
            self.turn_timer = int(turn_amount)
        except ValueError:
            pass

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

        await sendmessage(websocket, self.battle_id, "Well played! So far this session, my win:loss ratio has been: " + str(login.wins) + ":" + str(login.losses) + ".")
        await login.game_over(self)