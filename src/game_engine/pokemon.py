from enum import Enum

from src.game_engine.game_calcs import stat_calculation

class Status(Enum):
    """
    Status problem enumeration.
    """
    healthy = 0
    poisoned = 1
    toxic = 2
    paralyzed = 3
    burned = 4
    asleep = 5
    frozen = 6


def pokemon_from_json(pkm_name):
    """
    Filtrate, regroup and translate data from json files.
    :param pkm_name: Pokemon's name
    :return: Dict. {types, possibleAbilities, baseStats, possibleMoves}
    """

    pkm_name = pkm_name.lower().replace('-', '').replace(' ', '').replace('%', '').replace('\'', '').replace('.', '')
    res = {
        "types": [],
        "possibleAbilities": [],
        "baseStats": {},
        "possibleMoves": []
    }

    # All data should already be parsed and stored in our Login singleton
    from src.io_process.login import Login
    login = Login()
    pokemon = login.pokemon[pkm_name]
    res["types"] = pokemon["types"]
    res["possibleAbilities"] = list(pokemon["abilities"].values())
    res["baseStats"] = pokemon["baseStats"]
    try:
        pokemon_moves = login.format_moves[pkm_name]["randomBattleMoves"]
    except KeyError:
        login.forfeit_all_matches(RuntimeError("Could not find valid moves for " + pkm_name))
        return res
    moves = login.moves
    for move in pokemon_moves:
        res["possibleMoves"].append(moves[move])
    return res


class Pokemon:
    """
    Pokemon class.
    Handle everything corresponding to it.
    """
    def __init__(self, battle, name, condition, active, level):
        """
        Init Pokemon method.
        :param name: name of Pokemon.
        :param condition: ### TODO ###
        :param active: Bool.
        """
        self.battle = battle
        self.name = name
        self.current_health = 0
        self.max_health = 0
        self.condition = condition
        self.status = Status.healthy
        self.active = active
        self.level = int(level)
        self.types = []
        self.item = ""
        self.abilities = []
        self.base_stats = {}
        self.stats = {}
        self.moves = []
        self.substitute = False
        self.team = None
        self.buff = {
            "atk": [0, 1],
            "def": [0, 1],
            "spa": [0, 1],
            "spd": [0, 1],
            "spe": [0, 1],
            "accuracy": [0, 1],
            "evasion": [0, 1]
        }
        self.update_health(self.condition)

    def load_unknown(self):
        """
        Load every information of pokemon from datafiles and store them
        """
        infos = pokemon_from_json(self.name)
        self.types = infos["types"]
        self.abilities = infos["possibleAbilities"]
        self.base_stats = infos["baseStats"]
        self.moves = infos["possibleMoves"]

    def load_known(self, abilities, item, stats, moves):
        """
        Load ever information of pokemon from datafiles, but use only some of them.
        :param abilities: String. Ability of pokemon.
        :param item: String. Item of pokemon.
        :param stats: Dict. {hp, atk, def, spa, spd, spe}
        :param moves: Array. Not used.
        """
        infos = pokemon_from_json(self.name)
        self.types = infos["types"]
        self.abilities = abilities
        self.item = item
        self.base_stats = infos["baseStats"]
        self.stats = stats

        from src.io_process.login import Login
        login = Login()
        for move in moves:
            self.moves.append(login.moves[move.replace('60', '')])

    def get_stat_value(self, stat):
        """
        Gets the actual numerical value of the given stat.
        If the numerical value is unknown, gives a worst-case approximation
        """
        try:
            value = self.stats[stat]
        except KeyError:
            value = stat_calculation(self.base_stats[stat], self.level, 252) 
        return value

    def update_health(self, health_string):
        health = health_string.split('/')
        try:
            self.current_health = int(health[0])
            # Status conditions may follow the max health line
            # We split to strip the status conditions away
            health = health[1].split(' ')
            self.max_health = int(health[0])
        except IndexError:
            pass
        except ValueError:
            self.current_health = 0
            if self.max_health is 0:
                self.max_health = 100

    def is_fainted(self):
        return self.condition is "0 fnt"

    def get_hp_percent(self):
        if self.max_health is 0:
            if self.is_fainted():
                return 0
            else:
                return 1
        else:
            return self.current_health / self.max_health

    def cant_use_move(self, move_id):
        for i in range(len(self.moves)):
            if self.moves[i]['id'] is move_id:
                self.moves[i]['disabled'] = True
                return True
        return False

    def buff_affect(self, stat):
        """
        Return buff corresponding to stat
        :param stat: String : ["atk", "def", "spa", "spd", "spe"]
        :return: Float
        """
        return self.buff[stat][1]

    def __repr__(self):
        return str(vars(self))

    def __str__(self):
        output = self.name + " (" + str(self.status) + ")"
        output += " Condition: "
        if self.is_fainted():
            output += "Fainted"
        else:
            output += str(self.current_health) + "/" + str(self.max_health)
        if self.level < 100:
            output += " Level " + str(self.level)
        if self.item is not "" and self.item is not None:
            output += " @ " + str(self.item)
        output += "\nAbilities: " + str(self.abilities)
        output += "\nStats:"
        for stat in self.base_stats:
            print("\n - " + stat + ": " + str(self.get_stat_value(stat)))
        output += "\nMoves:"
        for move in self.moves:
            try:
                output += "\n" + move["name"]
                output += "\n - " + str(move["pp"]) + " PP"
                if move["disabled"]:
                    output += "\n - Move Disabled"
                else:
                    output += "\n - Move Enabled"
            except KeyError:
                pass
        output += "\nBuffs:"
        for stat in self.buff:
            output += "\n * " + stat + ": " + str(self.buff[stat])
        return output