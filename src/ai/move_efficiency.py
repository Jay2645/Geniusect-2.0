from math import floor

from src.game_engine.game_calcs import get_damage, Status
from src.helpers import player_id_to_index

def effi_boost(move, pkm1, pkm2):
    """
    Calculate if boost is worth or not. Currently only working on speed.
    :param move: Json object, status move.
    :param pkm1: Pokemon that will use move.
    :param pkm2: Pokemon that will receive move.
    :return: Boolean, True if worth, else False
    """
    value = 0
    tmp = {}
    pkm1_spe = pkm1.get_stat_value("spe")
    pkm2_spe = pkm2.get_stat_value("spe")
    for i in pkm1.moves:
        if i["name"] == move["move"]:
            tmp = i
    try:
        if "boosts" in tmp and "spe" in tmp["boosts"]:
            value = tmp["boosts"]["spe"]
        elif "self" in tmp and "boosts" in tmp["self"] and "spe" in tmp["self"]["boosts"]:
            value = tmp["self"]["boosts"]["spe"]
        elif ("secondary" in tmp and tmp["secondary"] and "self" in tmp["secondary"]
              and "boosts" in tmp["secondary"]["self"] and "spe" in tmp["secondary"]["self"]["boosts"]):
            value = tmp["secondary"]["self"]["boosts"]["spe"]
        if (pkm1.base_stats["spe"] * pkm1.buff_affect("spe") - pkm2.base_stats["spe"] * pkm2.buff_affect("spe") < 0
                and (pkm1_spe * pkm1.buff_affect("spe") + value * pkm1_spe - pkm2_spe * pkm2.buff_affect("spe") > 0)):
            return True
    except KeyError as e:
        print("\033[31m" + str(e) + "\n" + str(tmp) + "\033[0m")
    return False


def effi_status(move, pkm1, pkm2, team):
    """
    Efficiency status calculator.
    Give arbitrary value to status move depending on types, abilities and stats.
    :param move: Json object, status move.
    :param pkm1: Pokemon that will use move
    :param pkm2: Pokemon that will receive move
    :param team: Team of pkm1
    :return: Float, value of move [0, +oo[.
    """

    if pkm2.substitute:
        return 0
    elif "Synchronize" in pkm2.abilities:
        return 0
    elif move.id in ["toxic", "poisonpowder"]:
        if "Poison" in pkm2.types or "Steel" in pkm2.types:
            return 0
        return 100
    elif move.id in ["thunderwave", "stunspore", "glare"]:
        if "Electric" in pkm2.types or "Ground" in pkm2.types:
            return 0
        if pkm1.base_stats["spe"] - pkm2.base_stats["spe"] < 10:
            return 200
        return 100
    elif move.id == "willowisp":
        if "Fire" in pkm2.types:
            return 0
        if pkm2.base_stats["atk"] - pkm2.base_stats["spa"] > 10:
            return 200
        return 60
    else:
        for pkm in team.pokemon:  # Sleep clause
            if pkm.status == Status.asleep:
                return 0
        if move.id in ["spore", "sleeppowder"] and "Grass" in pkm2.types \
                or "Vital Spirit" in pkm2.abilities \
                or "Insomnia" in pkm2.abilities:
            return 0
        return 200

def entry_hazard_status(move, enemy_team):
    valid_pokemon = 5
    for pokemon in enemy_team.pokemon:
        if pokemon == enemy_team.active() or pokemon.condition == "0 fnt":
            valid_pokemon -= 1
    if valid_pokemon <= 0:
        # They can't switch, so don't bother
        print("Assigning " + move.name + " a weight of 0 as the enemy can't switch!")
        return 0

    if move.id == "stealthrock" and enemy_team.entry_hazards["stealth_rock"] > 0:
        return 0
    if move.id == "stickyweb" and enemy_team.entry_hazards["sticky_web"] > 0:
        return 0
    if move.id == "spikes" and enemy_team.entry_hazards["spikes"] >= 3:
        return 0
    if move.id == "toxicspikes" and enemy_team.entry_hazards["toxic_spikes"] >= 2:
        return 0

    return 50 * valid_pokemon

def entry_hazard_removal_status(move, team):
    valid_pokemon = 0
    for pokemon in team.pokemon:
        if pokemon != team.active() and pokemon.condition != "0 fnt":
            valid_pokemon += 1
    if valid_pokemon == 0:
        # We can't switch, so don't bother
        return 0

    effi = 0
    if team.entry_hazards["stealth_rock"] > 0:
        effi += 25
    if team.entry_hazards["sticky_web"] > 0:
        effi += 15
    effi += team.entry_hazards["spikes"] * 15
    effi += team.entry_hazards["toxic_spikes"] * 15
    return valid_pokemon * effi

def effi_move(battle, move, pkm1, pkm2, team):
    """
    Calculate efficiency of move based on previous functions, type, base damage and item.
    :param battle: Battle instance
    :param move: Json object, status move.
    :param pkm1: Pokemon that will use move
    :param pkm2: Pokemon that will receive move
    :param team: Team of pkm1
    :return: Float
    """

    if "reflectable" in move.flags and "Magic Bounce" in pkm2.abilities:
        return 0

    non_volatile_status_moves = [
        "toxic",  # tox
        "poisonpowder",  # psn
        "thunderwave", "stunspore", "glare",  # par
        "willowisp",  # brn
        "spore", "darkvoid", "sleeppowder", "sing", "grasswhistle", "hypnosis", "lovelykiss"  # slp
    ]

    entry_hazard_moves = [
        "stealthrock",
        "spikes",
        "toxicspikes",
        "stickyweb"
    ]
    entry_hazard_removal = [
        "defog",
        "rapidspin"
    ]

    if "No Guard" in pkm1.abilities or "No Guard" in pkm2.abilities:
        accuracy = 1
    else:
        accuracy = move.accuracy
        if accuracy > 1:
            accuracy /= 100

    if move.id in entry_hazard_moves:
        weight = entry_hazard_status(move, pkm2.team)
    elif move.id in entry_hazard_removal:
        weight = entry_hazard_removal_status(move, team)
        if move.id == "rapidspin":
            # Rapid Spin doesn't affect Ghost Types
            damage = get_damage(battle, pkm1, pkm2, move)
            if damage is not None:
                weight *= damage
    elif move.id in non_volatile_status_moves and pkm2.status == Status.healthy:
        weight = effi_status(move, pkm1, pkm2, team)
    else:
        weight = get_damage(battle, pkm1, pkm2, move)
        if weight is None:
            weight = 0

    modified_weight = weight * accuracy
    if pkm1.team.is_bot and pkm1.active:
        print("Assigning a weight of " + str(modified_weight) + " for " + pkm1.name + "'s " + move.name + " "+str(weight) + " plus " + str(accuracy))
    return modified_weight


def effi_pkm(battle, pkm1, pkm2, is_forced_switch):
    """
    Efficiency of pokemon against other.
    Based on move efficiency functions.
    If efficiency of a pokemon > 150 and is faster, efficiency of the other pokemon is not taken.
    effi_pkm(a, b, team_a) = - effi_pkm(b, a, team_b)
    :param battle: Battle object, current battle.
    :param pkm1: Pokemon that will use move.
    :param pkm2: Pokemon that will receive move.
    :return: Float, can be negative.
    """

    effi1 = 0
    pkm1_move_name = ""
    
    pkm2_max_hp = pkm2.get_stat_value("hp")

    pkm2_hp = floor(pkm2_max_hp * pkm2.get_hp_percent())

    # Find the move the attacker will use that does the most damage
    for move in pkm1.moves:
        dmg = effi_move(battle, move, pkm1, pkm2, pkm1.team)
        if effi1 < dmg:
            pkm1_move_name = move.name
            effi1 = dmg


    if not is_forced_switch:
        # Subtract the best possible move from the defender's current HP
        # This is the damage we'd take on the turn we switch in
        pkm2_hp -= effi1
        if pkm2_hp <= 0:
            print(pkm2.name + " will be killed in a switch by " + pkm1.name + " using " + pkm1_move_name)
            return 0

    # @TODO: Move this to its own function
    effi2 = 0
    pkm2_move_name = ""

    pkm1_spe = pkm1.get_stat_value("spe") * pkm1.buff_affect("spe")
    pkm2_spe = pkm2.get_stat_value("spe") * pkm2.buff_affect("spe")

    pkm1_max_hp = pkm1.get_stat_value("hp")
    pkm1_hp = floor(pkm1_max_hp * pkm1.get_hp_percent())

    # If we survive and outspeed, find out how much damage we will do
    for move in pkm2.moves:
        dmg = effi_move(battle, move, pkm2, pkm1, pkm2.team)
        if effi2 < dmg:
            effi2 = dmg
            pkm2_move_name = move.name

    # Subtract our attack from the attacker's HP
    pkm1_hp -= effi2
    if pkm1_hp <= 0 and pkm1_spe > pkm2_spe:
        # We killed them!
        print(pkm2.name + " will survive a switch and then outspeed and kill " + pkm1.name + " using " + pkm2_move_name)
        return effi2
    else:
        # We won't outspeed, so we'll take damage first
        pkm2_hp -= effi1
        if pkm2_hp <= 0:
            # The move will kill us, so we can't attack at all
            # Give them their missing HP back
            # (This will in turn give this Pokemon a lower score)
            pkm1_hp += effi2

    # Get HP percentage values in range 0 - 100
    pkm1_hp_percent = (pkm1_hp / pkm1.get_stat_value("hp")) * 100
    pkm2_hp_percent = (pkm2_hp / pkm2.get_stat_value("hp")) * 100

    speed_status = "will outspeed" if pkm1_spe > pkm2_spe else "will survive a hit"

    print("After a switch, " + pkm1.name + " (attacker) " + speed_status + " and use move " + pkm1_move_name + " with " + str(pkm1_hp_percent) + "% HP (" + str(pkm1_hp) + "/" + str(pkm1_max_hp) + ")")
    print(pkm2.name + " (defender) will use move " + pkm2_move_name + " and have " + str(pkm2_hp_percent) + "% HP (" + str(pkm2_hp) + "/" + str(pkm2_max_hp) + ")")

    # Return the difference between how much damage we do and how much damage they do
    delta = pkm2_hp_percent - pkm1_hp_percent

    return delta