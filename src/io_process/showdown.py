#!/usr/bin/env python3

import requests
import asyncio
import websockets
import sys

from src.helpers import Singleton, singleton_object
from src.io_process import senders, json_loader
from src.io_process.match import Match
from src.ui.user_interface import UserInterface

from src.ai.ai import AI
from src.ai.traditional.traditional_ai import TraditionalAI

avatar = 117
MAX_FIGHT_COUNT = 4
ai = TraditionalAI()

def shutdown_showdown():
    print("Shutting down Pokemon Showdown!")
    showdown = Showdown()
    if showdown.forfeit_exception is None:
        showdown.forfeit_all_matches()
    else:
        raise showdown.forfeit_exception

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
        if resp.status_code != 200:
            raise ConnectionError(f"Request failed with status code {resp.status_code}. Details: {resp.reason}")
        ui = UserInterface()
        ui.on_logged_in(self.username)

        await senders.set_nickname(self.websocket, self.username, resp.text[1:])
        await senders.set_avatar(self.websocket, avatar)
        print("Showdown connection successful, ready for battle!")

        await self.search_for_fights()

    async def search_for_fights(self):
        if not self.allow_new_matches:
            # No more matches
            return

        # Once we are connected.
        challenge_format = self.formats[0]

        if MAX_FIGHT_COUNT <= 0 or (self.wins + self.losses) < MAX_FIGHT_COUNT:
            ui = UserInterface()
            challenge_mode = ui.get_selected_challenge_mode()
            if challenge_mode == 1:
                challenge_player = ui.get_challenger_name()
                print("Challenging " + challenge_player + " using " + challenge_format)
                await senders.challenge(self.websocket, challenge_player, self.formats[0])
            elif challenge_mode == 2:
                print("Searching for a match on the " + challenge_format + " ladder.")
                await senders.searching(self.websocket, challenge_format)
            else:
                print("Awaiting challengers...")
        else:
            print(f"All done! Win:Loss ratio: {self.wins}:{self.losses}")

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

    async def create_battle(self, battle_id : str) -> Match:
        if not self.allow_new_matches:
            return

        print("Starting new battle!")

        battle = Match(battle_id, ai)
        battle.open_match_window()
        self.battles.append(battle)
        await senders.start_timer(self.websocket, battle.battle_id)
        return battle

    async def game_over(self, battle):
        if battle is None:
            return

        print("Game is over")

        if self.forfeit_exception is not None:
            await senders.sendmessage(self.websocket, battle.battle_id, "Oops, I crashed! Exception data: " + str(type(self.forfeit_exception)) + ": " + str(self.forfeit_exception) + ". You win!")
        
        await senders.leaving(self.websocket, battle.battle_id)
        self.battles.remove(battle)
        if self.forfeit_exception is None:
            ui = UserInterface()
            ui.match_over(battle.battle_id)
            await self.search_for_fights()

    async def deinit_game(self):
        if self.forfeit_exception is not None:
            return
        forfeit_all_matches(self.forfeit_exception)

    def forfeit_all_matches(self, exception=None):
        if self.forfeit_exception is None:
            self.forfeit_exception = exception
        
        print("We hit an exception; exiting everything")
        self.forfeit_exception = exception
        self.allow_new_matches = False

        ui = UserInterface()
        ui.raise_error(self.forfeit_exception)
        #ui.close_windows()
        
        for battle in self.battles:
            asyncio.get_event_loop().create_task(self.forfeit(battle))
        
        
    async def forfeit(self, battle):
        print("Forfeiting battle " + battle.battle_id + "!")
        await senders.forfeit_match(self.websocket, battle.battle_id)
        await self.game_over(battle)

    def log_out(self):
        ui = UserInterface()
        ui.close_windows()
        print("Logging out.")
        #exit(0)