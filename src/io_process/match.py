#!/usr/bin/env python3

from src.io_process import senders

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

    def __init__(self, match_id : str):
        self.battle_id = match_id
        self.turn = 0
        self.player_id = 0
        self.request_id = 0
        self.battle_text = ""
        self.turn_text = ""
        print("Created match.")

    def update_server_message(self, server_message):
        if self.turn <= 0:
            return

        if self.turn_text != "":
            self.turn_text += "\n----------\n"

        self.turn_text += server_message

    def new_turn(self):
        self.turn += 2
        self.turn_text = ""
        print("Beginning turn " + str(self.turn))

    def get_match_state(self):
        return self.battle_text + "\n" + self.turn_text

    def set_request_id(self, request_body, request_id):
        self.battle_text = request_body
        self.request_id = request_id

    def get_request_id(self):
        return self.request_id

    async def new_player_joined(self, websocket, username : str):
        await senders.sendmessage(websocket, self.battle_id, "Hi, " + username + "! I'm a bot! I'm probably going to crash and forfeit at some point, so be nice!")

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