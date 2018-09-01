
from src.game_engine.battle import Battle
from src.helpers import player_id_to_index

class Match:
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
        self.tier = ""

    def set_player_name(self, player_id, player_name):
        from src.io_process.showdown import Showdown
        login = Showdown()
        is_us = login.username.lower() == player_name.lower()

        player_index = player_id_to_index(player_id)
        self.sides[player_index]['name'] = player_name
        self.sides[player_index]['showdown_id'] = player_id
        self.sides[player_index]['is_bot'] = is_us

        self.battle.update_player(self.sides[player_index], player_index)

    def set_team_size(self, player_id, team_size):
        player_index = player_id_to_index(player_id)
        self.sides[player_index]['team_size'] = team_size

        self.battle.update_player(self.sides[player_index], player_index)

    def set_generation(self, generation):
        self.gen = int(generation)

    def set_tier(self, tier):
        self.tier = tier

    async def send_request(self, request):
        await self.battle.req_loader(request)

    async def new_turn(self, turn_number):
        self.turn = int(turn_number)
        await self.battle.new_turn(self.turn)