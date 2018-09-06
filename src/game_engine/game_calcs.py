#!/usr/bin/env python3

from math import floor
from enum import Enum

from src.io_process import json_loader

class Status(Enum):
    """
    Status problem enumeration.
    """
    none = -1
    healthy = 0
    poisoned = 1
    toxic = 2
    paralyzed = 3
    burned = 4
    asleep = 5
    frozen = 6
    fainted = 7

def stat_calculation(base, level, ev):
    """
    Calculation of stats based on base stat, level and ev.
    IVs are maxed, nature is not used.
    Cannot be used for HP calculation.
    :param base: Integer, base stat of wanted stat.
    :param level: Integer, level of pokemon.
    :param ev: Integer [0, 252] quantity of ev.
    :return: Ingeger, actual stat.
    """
    return floor(((2 * base + 31 + floor(ev / 4)) * level) / 100 + 5)


def efficiency(elem: str, elems: [str]):
    """
    Type chart calculator.
    :param elem: Elem of move.
    :param elems: Elements of target pokemon.
    :return: Float, efficiency multiplication.
    """
    res = 1
    for target_elem in elems:
        tmp = json_loader.typechart[target_elem]['damageTaken'][elem]
        if tmp == 1:
            res *= 2
        elif tmp == 2:
            res *= 0.5
        elif tmp == 3:
            res *= 0
    return res


def side_modifier(move, team):
    """
    Side modifiers, like screens, entry hazards, etc.
    :param move: Json object, move.
    :param pkm2: Team taking the hit
    :return: Float [0; +oo]
    """
    if move.category == "Special" and team is not None and team.light_screen:
        return 0.5
    elif move.category == "Physical" and team is not None and team.reflect:
        return 0.5
    else:
        return 1


def item_modifier(move, pkm1, pkm2):
    """
    Calculation of item modifier
    :param move: Json object, move.
    :param pkm1: Pokemon that will use move.
    :param pkm2: Pokemon that will receive move.
    :return: Float [0; +oo]
    """
    mod = 1
    if pkm1.item == "lifeorb":
        mod *= 1.3
    elif pkm1.item == "expertbelt" and efficiency(move.type, pkm2.types) > 1:
        mod *= 1.2
    elif pkm1.item == "choicespecs" and move.category == "Special":
        mod *= 1.5
    elif pkm1.item == "choiceband" and move.category == "Physical":
        mod *= 1.5
    elif pkm1.item == "thickclub" and move.category == "Physical":
        mod *= 1.5

    return mod

def our_ability_modifier(move, pkm1, pkm2):
    mod = 1
    from src.game_engine.pokemon import Status
    if "Tinted Lens" in pkm1.abilities and efficiency(move.type, pkm2.types) < 1:
        mod *= 2
    elif "Guts" in pkm1.abilities and pkm1.status != Status.healthy and move.category == "Physical":
        mod *= 1.5
    if "Fluffy" in pkm2.abilities:
        if "contact" in move.flags.keys():
            mod *= 0.5
        elif move.type == "Fire" and "contact" not in move.flags.keys():
            mod *= 2
    return mod


def their_ability_modifier(type, pkm2):
    """
    Calculation of ability modifier
    :param type: The type of move being used ("Water", "Ground", etc.)
    :param pkm2: Pokemon that will receive move.
    :return: Float [0; +oo]
    """
    mod = 1
    
    if "Solid Rock" in pkm2.abilities and efficiency(type, pkm2.types) > 1:
        mod *= 0.75
    elif "Filter" in pkm2.abilities and efficiency(type, pkm2.types) > 1:
        mod *= 0.75
    elif "Prism Armor" in pkm2.abilities and efficiency(type, pkm2.types) > 1:
        mod *= 0.75
    elif "Levitate" in pkm2.abilities and type == "Ground":
        mod = 0
    elif "Water Absorb" in pkm2.abilities and type == "Water":
        mod = 0
    elif "Volt Absorb" in pkm2.abilities and type == "Electric":
        mod = 0
    elif "Flash Fire" in pkm2.abilities and type == "Fire":
        mod = 0
    return mod

def type_damage_calculation(type, pkm2):
    """
    Damage type calculation
    :param type: Type of move being used
    :param pkm2: Pokemon that will receive move.
    :return: Float, damage of move [0, +oo].
    """
    effi = efficiency(type, pkm2.types)
    ability_modifier = their_ability_modifier(type, pkm2)
    # Handled here so we can be more accurate when calling this function by itself
    # Otherwise we would have to calculate the exact damage taken when we just want this one modifier
    if pkm2.item == "airballoon" and type == "Ground":
        mod = 0
    else:
        mod = 1
    
    return mod * effi * ability_modifier


def damage_calculation(battle, move, pkm1, pkm2):
    """
    Damage move calculation.
    :param battle: Battle, used for side modifier.
    :param move: Json object, status move.
    :param pkm1: Pokemon that will use move.
    :param pkm2: Pokemon that will receive move.
    :return: Float, damage of move [0, +oo].
    """

    # Determine which values we're operating on
    category = ("spa", "spd") if move.category == "Special" else ("atk", "def")

    # Calculate actual attack and defense stats
    atk = pkm1.get_stat_value(category[0]) * pkm1.buff_affect(category[0])
    defe = pkm2.get_stat_value(category[1]) * pkm2.buff_affect(category[1])

    # Store move power
    power = move.base_power

    # Calculate Same Type Attack Bonus (STAB)
    stab = 1.5 if move.type in pkm1.types else 1

    # Calculate effectiveness (super-effective, not very effective, no effect, stored as a float damage modifier)
    effi = type_damage_calculation(move.type, pkm2)

    # When a Pokemon is burned, its physical attacks do half damage
    from src.game_engine.pokemon import Status
    if category[0] is "atk" and pkm1.status == Status.burned and "Guts" not in pkm1.abilities:
        # Guts is handled by the ability modifier
        burn = 0.5
    else:
        burn = 1

    # Calculate extra damage done by any held items
    item_mod = item_modifier(move, pkm1, pkm2)

    # Calculate any extra damage taken by our ability or the move we're using
    # (Damage negation from the other Pokemon's abilities is handled by type_damage_calculation)
    ability_mod = our_ability_modifier(move, pkm1, pkm2)

    # Calculate any damage reduction from field abilities like light screen and reflect
    side_mod = side_modifier(move, pkm2.team)

    # @TODO: Calculate weather modifiers

    # Multiply all modifiers together
    all_modifiers = stab * effi * burn * item_mod * ability_mod * side_mod
    # Calculate final damage output
    return floor(floor(((0.4 * pkm1.level + 2) * (atk / defe) * power) / 50 + 2) * all_modifiers)