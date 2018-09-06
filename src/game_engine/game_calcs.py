#!/usr/bin/env python3

from math import floor
from enum import Enum

from src.io_process import json_loader

def get_typechart():
    from src.io_processs.login import Showdown
    login = Showdown()
    return login.typechart

def get_effect(name):
    if name is None or name is "":
        return None
    if type(name) is not str:
        return name

    if 'move:' in name:
        return get_move(name[5:])
    elif 'item:' in name:
        return get_item(name[5:])
    elif 'ability:' in name:
        return get_ability(name[8:])

    id = string_to_id(name)


def get_immunity(source_type, target_types):
    """
	Returns false if the target is immune; true otherwise
	Also checks immunity to some statuses
	:param source_type: String. The type of move that needs to check for immunity.
    :param target_types: List of strings. The types of the Pokemon recieving the move.
    :return: Boolean. False if we are immune, else True if we can take damage
    """

    # Grab typechart
    typechart = get_typechart()

    for target_type in target_types:
        if typechart[target_type]['damageTaken'][source_type] is 3:
            return False
    return True

def get_effectiveness(source_type, target_types):
    """
	Returns a value between -2 and 2 regarding how effective a move would be.
    A value of 0 is normal effectiveness, -2 is 0.25x, 2 is 4x.
    Immunity is not handled here; use get_immunity().
	:param source_type: String. The type of move that needs to check for effectiveness.
    :param target_types: List of strings. The types of the Pokemon recieving the move.
    :return: Integer, [-2, 2]
    """
    
    # Grab typechart
    typechart = get_typechart()

    total_type_mod = 0
    for target_type in target_types:
        effectiveness = typechart[target_type]['damageTaken'][source_type]
        if effectiveness is 1:
            # It's super effective!
            total_type_mod += 1
        elif effectiveness is 2:
            # It's not very effective...
            total_type_mod -= 1
        # This doesn't take into account the circumstances of the battle
        # Things like abilities and gravity are handled elsewhere
    return total_type_mod

def spread_modify(base_stats, pokemon, pokemon_evs = None, pokemon_ivs = None, nature = "docile"):
    if pokemon_ivs is None:
        pokemon_ivs = {
            "atk": 31,
            "def": 31,
            "hp": 31,
            "spa": 31,
            "spd": 31,
            "spe": 31,
        }
    if pokemon_evs is None:
        pokemon_evs = {
            "atk": 0,
            "def": 0,
            "hp": 0,
            "spa": 0,
            "spd": 0,
            "spe": 0,
        }

    modified_stats = {
        "atk": 0,
        "def": 0,
        "hp": 0,
        "spa": 0,
        "spd": 0,
        "spe": 0,
    }

    for stat in base_stats:
        modified_stats[stat] = stat_calculation(base_stats[stat], pokemon_evs[stat], pokemon_ivs[stat], pokemon.level)
    return nature_modify(modified_stats, nature)

def stat_calculation(stat_amount, ev = 252, iv = 31, level = 100):
    base_stat_calc = 2 * stat_amount + iv + floor(ev / 4)
    if stat is "hp":
        # HP has a weird calculation
        return floor(floor(base_stat_calc + 100) * level / 100 + 10)
    else:
        return floor(floor(base_stat_calc) * level / 100 + 5)


def nature_modify(pokemon_stats, nature):
    try:
        nature_type = battle_natures[nature]
        positive_stat = nature_type['plus']
        negative_stat = nature_type['minus']
        pokemon_stats[positive_stat] *= 1.1
        pokemon_stats[negative_stat] *= 0.9
    except KeyError:
        pass
    return pokemon_stats

def get_damage(battle, attacker, defender, move):

    # Check for immunity
    if not move.ignore_immunity and not defender.run_immunity(move.type):
        # Defender is immune to this move
        # Returning None means we are not dealing damage
        return None

    if move.one_hit_ko:
        return defender.get_stat_value('hp')

    if move.does_damage_based_on_level:
        # Seismic Toss, Nightshade
        return attacker.level
    if move.set_damage_amount > 0:
        # Dragon Rage always does 40 HP
        return move.set_damage_amount

    if move.base_power is 0:
        return None

    move_will_crit = move.will_crit
    # Here we could actually calculate the crit percentage
    # However, this would screw up AI predictions in long-term planning
    # If it always considers the worst-case scenario (crit every turn),
    # then it would never use defensive moves (as crits ignore defensive buffs)
    if move_will_crit:
        move_will_crit = battle.run_event('CriticalHit', defender, None, move)

    return run_damage_formula(battle, attacker, defender, move_will_crit)

def run_damage_formula(battle, attacker, defender, move, is_crit, best_case = True):
    base_power = battle.run_event('BasePower', attacker, defender, move, move.base_power, True)
    if base_power <= 0:
        # Event may modify the base power
        return 0

    attack_stat = 'atk' if move.category is 'Physical' else 'spa'
    defense_stat = 'def' if move.defensive_category is 'Physical' else 'spd'
    stat_table = {
        "atk": "Atk", 
        "def": "Def", 
        "spa": "SpA", 
        "spd": "SpD", 
        "spe": "Spe"
    }

    if not is_crit:
        is_crit = move.will_crit

    attack_boosts = defender.boosts[attack_stat] if move.use_defender_offensive_stat else attacker.boosts[attack_stat]
    defense_boosts = attacker.boosts[defense_stat] if move.use_attacker_defense_stat else defender.boosts[defense_stat]
    
    ignore_negative_offensive = is_crit or move.ignore_negative_offensive
    ignore_positive_defensive = is_crit or move.ignore_positive_defensive
    
    ignore_offensive = move.ignore_offensive or ignore_negative_offensive and attack_boosts < 0
    ignore_defensive = move.ignore_defensive or ignore_positive_defensive and defense_boosts > 0

    if ignore_offensive:
        print("Negating " + attack_stat + " boost/penalty.")
        attack_boosts = 0
    if ignore_defensive:
        print("Negating " + defense_stat + " boost/penalty.")
        defense_boosts = 0

    if move.use_defender_offensive_stat:
        attack = defender.calculate_stat(attack_stat, attack_boosts)
    else:
        attack = attacker.calculate_stat(attack_stat, attack_boosts)

    if move.use_attacker_defense_stat:
        defense = attacker.calculate_stat(defense_stat, defense_boosts)
    else:
        defense = defender.calculate_stat(defense_stat, defense_boosts)
        
    # Apply Stat Modifiers
    attack = battle.run_event('Modify' + stat_table[attackStat], attacker, defender, move, attack)
    defense = battle.run_event('Modify' + stat_table[defenseStat], defender, attacker, move, defense)

    # int(int(int(2 * L / 5 + 2) * A * P / D) / 50)
    base_damage = floor(floor(floor(2 * attacker.level / 5 + 2) * base_power * attack / defense) / 50)

    return modify_damage(base_damage, battle, attacker, defender, move, is_crit)

def modify_damage(base_damage, battle, attacker, defender, move, is_crit, best_case):
    move_type = move.type
    base_damage += 2

    # @TODO: Doubles support, spread hit

    base_damage = battle.run_event('WeatherModifyDamage', attacker, defender, move, base_damage)

    if is_crit:
        base_damage *= move.crit_modifier

    if not best_case:
        # Moves do a random amount of damage
        # If we're not in the best-case scenario, assume we're in the worst-case scenario
        base_damage = floor(base_damage * (21 / 25))

    if attacker.has_type(move_type):
        base_damage *= 1.5

    type_effectiveness = defender.run_effectiveness(move)
    if type_effectiveness < -6:
        type_effectiveness = -6
    elif type_effectiveness > 6:
        type_effectiveness = 6

    if type_effectiveness > 0:
        # It's super-effective!
        for i in range(type_effectiveness):
            base_damage *= 2
    elif type_effectiveness < 0:
        # It's not very effective...
        for i in range(0, type_effectiveness, -1):
            base_damage = floor(base_damage / 2)

    if attacker.status is Status.BRN and move.category is 'Physical' and not attacker.has_ability('guts'):
        if move.id is not 'facade':
            base_damage = floor(base_damage / 2)

    # Final modifier. Modifiers that modify damage after min damage check, such as Life Orb.
    base_damage = battle.run_event('ModifyDamage', pokemon, target, move, baseDamage)

    if move.is_z_move and move.z_broke_protect:
        base_damage = floor(base_damage / 4)

    if base_damage <= 0:
        return 1
    else:
        return base_damage