import sys
import json
import requests
import asyncio

from src.io_process import senders
from src.helpers import Singleton, singleton_object
from src.game_engine.battle import Battle

challenge_mode = 1
challenge_player = "EnglishMobster"

@singleton_object
class Login(metaclass=Singleton):
    """
    Login class.
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
        self.challenge_mode = challenge_mode
        self.challenge_player = challenge_player
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

    def load_json(self):
        print("Validating JSON")

        with open('data/pokedex.json', encoding='utf-8') as pokedex_file:
            self.pokemon = json.load(pokedex_file)
        print("Pokedex OK")
        with open('data/formats-data.json') as formats_file:
            self.format_moves = json.load(formats_file)
        print("Battle formats OK")
        with open("data/moves.json") as moves_file:
            self.moves = json.load(moves_file)
        print("Moves OK")
        with open("data/typechart.json") as typechart_file:
            self.typechart = json.load(typechart_file)
        print("Typechart OK")
        
        print("All JSON has been loaded!")


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
        await senders.sender(self.websocket, "", "/trn " + self.username + ",0," + json.loads(resp.text[1:])['assertion'])
        await senders.sender(self.websocket, "", "/avatar 159")

    async def search_for_fights(self):
        # Once we are connected.
        if self.challenge_mode == 1:
            await senders.challenge(self.websocket, self.challenge_player, self.formats[0])
        elif self.challenge_mode == 2:
            await senders.searching(self.websocket, self.formats[0])

    def check_battle(self, battle_id) -> Battle or None:
        """
        Get Battle corresponding to room_id.
        :param battle_list: Array of Battles.
        :param battle_id: String, Tag of Battle.
        :return: Battle.
        """
        for battle in self.battles:
            if battle.battle_id == battle_id:
                return battle
        return None

    async def create_battle(self, battle_id):
        if not self.allow_new_matches:
            return

        print("Starting new battle!")

        battle = Battle(battle_id)
        self.battles.append(battle)
        await senders.sendmessage(self.websocket, battle.battle_id, "Hi! I'm a bot! I'm probably going to crash and forfeit at some point, so be nice!")
        await senders.start_timer(self.websocket, battle.battle_id)

    async def game_over(self, battle):
        if battle is None:
            return

        print("Game is over")

        if self.forfeit_exception is None:
            await senders.sendmessage(self.websocket, battle.battle_id, "Well played!")
        else:
            await senders.sendmessage(self.websocket, battle.battle_id, "Oops, I crashed! Exception data: " + str(self.forfeit_exception) + ". You win!")
            import traceback
            traceback.print_tb(self.forfeit_exception.__traceback__)
        
        await senders.leaving(self.websocket, battle.battle_id)
        self.battles.remove(battle)


    def forfeit_all_matches(self, exception=None):
        self.forfeit_exception = exception
        self.allow_new_matches = False
        asyncio.get_event_loop().create_task(self.__forfeit__())

    async def forfeit(self, battle):
        print("Forfeiting battle " + battle.battle_id + "!")
        await senders.forfeit_match(self.websocket, battle.battle_id)
        await self.game_over(battle)

    async def __forfeit__(self):
        print("Forfeiting the game!")
        for battle in self.battles:
            await self.forfeit(battle)
        if self.forfeit_exception is not None:
            raise self.forfeit_exception

    def log_out(self):
        print("Logging out.")
        exit(0)