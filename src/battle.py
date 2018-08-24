import re
import json
from json import JSONDecodeError

from src.ia import make_best_action, make_best_switch, make_best_move, make_best_order
from src.pokemon import Pokemon, Team, Status
from src import senders


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
        self.bot_team = Team()
        self.enemy_team = Team()
        self.current_pkm = None
        self.turn = 0
        self.battle_id = battle_id
        self.player_id = ""
        self.screens = {
            "lightscreen": False,
            "reflect": False
        }
        print("Battle started")

    async def req_loader(self, req, websocket):
        """
        Parse and translate json send by server. Reload bot team. Called each turn.
        :param req: json sent by server.
        :param websocket: Websocket stream.
        """
        if req is "":
            print("Null request")
            return

        print("Beginning new turn")

        try:
            jsonobj = json.loads(req)
        except JSONDecodeError as e:
            print("JSON decode error: " + str(e))
            print("Request: " + req)
            from src.login import Login
            login = Login()
            login.forfeit_match(self)
            return

        self.turn += 2
        objteam = jsonobj['side']['pokemon']
        self.bot_team = Team()

        if "active" in jsonobj.keys():
            self.current_pkm = jsonobj["active"]

        for pkm in objteam:
            try:
                newpkm = Pokemon(self, pkm['details'].split(',')[0], pkm['condition'], pkm['active'],
                                 pkm['details'].split(',')[1].split('L')[1]
                                 if len(pkm['details']) > 1 and 'L' in pkm['details'] else 100)
                newpkm.load_known([pkm['baseAbility']], pkm["item"], pkm['stats'], pkm['moves'])
                self.bot_team.add(newpkm)
            except IndexError as e:
                print("\033[31m" + "IndexError: " + str(e))
                print(pkm + "\033[0m")
                from src.login import Login
                login = Login()
                login.forfeit_match(self)
                return

        if "forceSwitch" in jsonobj.keys():
            await self.make_switch(websocket)

    def update_enemy(self, pkm_name, level, condition):
        """
        On first turn, and each time enemy switch, update enemy team and enemy current pokemon.
        :param pkm_name: Pokemon's name
        :param level: int, Pokemon's level
        :param condition: str current_hp/total_hp. /100 if enemy pkm.
        """
        if "-mega" in pkm_name.lower():
            self.enemy_team.remove(pkm_name.lower().split("-mega")[0])
        if "-*" in pkm_name.lower():
            pkm_name = re.sub(r"(.+)-\*", r"\1", pkm_name)
        elif re.compile(r".+-.*").search(pkm_name.lower()):
            try:
                self.enemy_team.remove(re.sub(r"(.+)-.+", r"\1", pkm_name))
            except NameError:
                pass

        if pkm_name not in self.enemy_team:
            for pkm in self.enemy_team.pokemons:
                pkm.active = False
            pkm = Pokemon(self, pkm_name, condition, True, level)
            pkm.load_unknown()
            self.enemy_team.add(pkm)
        else:
            for pkm in self.enemy_team.pokemons:
                if pkm.name.lower() == pkm_name.lower():
                    pkm.active = True
                else:
                    pkm.active = False

    @staticmethod
    def update_status(pokemon, status: str = ""):
        """
        Update status problem.
        :param pokemon: Pokemon.
        :param status: String.
        """
        if status == "tox":
            pokemon.status = Status.TOX
        elif status == "brn":
            pokemon.status = Status.BRN
        elif status == "par":
            pokemon.status = Status.PAR
        elif status == "tox":
            pokemon.status = Status.TOX
        elif status == "slp":
            pokemon.status = Status.SLP
        else:
            pokemon.status = Status.UNK

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
        print("Making a move")
        if not best_move:
            best_move = make_best_move(self)
        if best_move[1] < 20:
            print("Best move power < 20. Move list : "
                  + ", ".join([move["move"] for move in self.current_pkm[0]['moves']]) + ".")
        if "canMegaEvo" in self.current_pkm[0]:
            await senders.sendmove(websocket, self.battle_id, str(best_move[0]) + " mega", self.turn)
        else:
            await senders.sendmove(websocket, self.battle_id, best_move[0], self.turn)

    async def make_switch(self, websocket, best_switch=None):
        """
        Call function to send swich and use the sendswitch sender.
        :param websocket: Websocket stream.
        :param best_switch: int, id of pokemon to switch.
        """
        print("Making a switch")
        if not best_switch:
            best_switch = make_best_switch(self)[0]
        await senders.sendswitch(websocket, self.battle_id, best_switch, self.turn)

    async def make_action(self, websocket):
        """
        Launch best action chooser and call corresponding functions.
        :param websocket: Websocket stream.
        """

        action = make_best_action(self)
        if action[0] == "move":
            print("Sending move request to server")
            await self.make_move(websocket, action[1:])
        if action[0] == "switch":
            print("Sending switch request to server")
            await self.make_switch(websocket, action[1])
