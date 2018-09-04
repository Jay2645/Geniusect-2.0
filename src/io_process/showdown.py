#!/usr/bin/env python3

import requests
import asyncio
import websockets
import sys

from src.helpers import Singleton, singleton_object
from src.io_process import senders, json_loader
from src.io_process.match import Match
from src.ui.user_interface import UserInterface

avatar = 117

def shutdown_showdown():
    showdown = Showdown()
    showdown.forfeit_all_matches()

async def create_websocket():
    global should_shutdown

    from src.io_process.io_processing import string_to_action
    with open("log.txt", "a", encoding='utf-8') as log_file:
        log_file.write("\n\n\nShowdown Logs:")
        async with websockets.connect('ws://sim.smogon.com:8000/showdown/websocket') as websocket:
            while True:
                message = await websocket.recv()
                log_file.write("\nLog: " + message)
                await string_to_action(websocket, message)

@singleton_object
class Showdown(metaclass=Singleton):
    """
    Showdown class.
    Handles everything related to logging in to the server.
    Responsible for handling server-wide states (websockets, username)
    """

    def __init__(self):
        """
        init Battle method.
        :param challenge_mode: 0: Only recieving. 1 Challenging a particular player. 2 searching random battles.
        :param challenge_player: If challenge_mode is set to 1, will challenge this player
        """
        with open(sys.path[0] + "/src/id.txt") as logfile:
            self.username = logfile.readline()[:-1]
            self.password = logfile.readline()[:-1]
        self.websocket = None
        self.battles = []
        self.forfeit_exception = None
        self.allow_new_matches = True
        self.formats = [
            "gen7randombattle",
            "gen7monotyperandombattle",
            "gen7hackmonscup",
            "gen7challengecup1v1",
            "gen6battlefactory",
            "gen7bssfactory"
        ]
        self.wins = 0
        self.losses = 0


    def update_websocket(self, websocket):
        """
        Updates our websocket with the most recent input from the server.
        :param websocket: The websocket stream
        """
        self.websocket = websocket

    async def log_in(self, challid, chall):
        """
        Login function. Send post request to Showdown server.
        :param challid: first part of login challstr sent by server
        :param chall: second part of login challstr sent by server
        """
        if self.websocket is None:
            raise ConnectionError("Websocket was never specified")

        print("Logging in as " + self.username + " with password " + self.password)
        resp = requests.post("https://play.pokemonshowdown.com/action.php?",
                             data={
                                'act': 'login',
                                'name': self.username,
                                'pass': self.password,
                                'challstr': challid + "%7C" + chall
                             })
        ui = UserInterface()
        ui.on_logged_in(self.username)

        await senders.set_nickname(self.websocket, self.username, resp.text[1:])
        await senders.set_avatar(self.websocket, avatar)

    async def search_for_fights(self):
        # Once we are connected.
        
        ui = UserInterface()
        challenge_mode = ui.get_selected_challenge_mode()

        challenge_format = self.formats[0]
        if challenge_mode == 1:
            challenge_player = ui.get_challenger_name()
            print("Challenging " + challenge_player + " using " + challenge_format)
            await senders.challenge(self.websocket, challenge_player, self.formats[0])
        elif challenge_mode == 2:
            print("Searching for a match on the " + challenge_format + " ladder.")
            await senders.searching(self.websocket, challenge_format)

    def check_battle(self, battle_id) -> Match or None:
        """
        Get Match corresponding to room_id.
        :param battle_id: String, Tag of Battle.
        :return: Match.
        """
        for battle in self.battles:
            if battle.battle_id == battle_id:
                return battle
        return None

    async def create_battle(self, battle_id):
        if not self.allow_new_matches:
            return

        print("Starting new battle!")

        battle = Match(battle_id)
        battle.open_match_window()
        self.battles.append(battle)
        await senders.start_timer(self.websocket, battle.battle_id)

    async def game_over(self, battle):
        if battle is None:
            return

        print("Game is over")

        if self.forfeit_exception is None:
            await senders.leaving(self.websocket, battle.battle_id)
        else:
            await senders.sendmessage(self.websocket, battle.battle_id, "Oops, I crashed! Exception data: " + str(self.forfeit_exception) + ". You win!")
            import traceback
            traceback.print_tb(self.forfeit_exception.__traceback__)
        
        self.battles.remove(battle)
        await senders.leaving(self.websocket, battle.battle_id)

    def forfeit_all_matches(self, exception=None):
        self.forfeit_exception = exception
        self.allow_new_matches = False
        asyncio.get_event_loop().create_task(self.__forfeit())
        ui = UserInterface()
        ui.close_windows()

    async def forfeit(self, battle):
        print("Forfeiting battle " + battle.battle_id + "!")
        await senders.forfeit_match(self.websocket, battle.battle_id)
        await self.game_over(battle)
        
    async def __forfeit(self):
        print("Forfeiting the game!")
        for battle in self.battles:
            await self.forfeit(battle)
        if self.forfeit_exception is not None:
            raise self.forfeit_exception

    def log_out(self):
        ui = UserInterface()
        ui.close_windows()
        print("Logging out.")
        exit(0)