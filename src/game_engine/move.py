#!/usr/bin/env python3

from enum import Flag, auto

from src.game_engine.effects import Entity
from src.io_process import json_loader


class MoveFlag(Flag):
    """
    Various flags that can be set on a Move object.
    """

    none = 0
    # Ignores a target's substitute.
    authentic = auto()
    # Power is multiplied by 1.5 when used by a Pokemon with the Ability Strong Jaw.
    bite = auto()
    # Has no effect on Pokemon with the Ability Bulletproof.
    bullet = auto()
    # The user is unable to make a move between turns.
    charge = auto()
    # Makes contact.
    contact = auto()
    # When used by a Pokemon, other Pokemon with the Ability Dancer can attempt to execute the same move.
    dance = auto()
    # Thaws the user if executed successfully while the user is frozen.
    defrost = auto()
    # Can target a Pokemon positioned anywhere in a Triple Battle.
    distance = auto()
    # Prevented from being executed or selected during Gravity's effect.
    gravity = auto()
    # Prevented from being executed or selected during Heal Block's effect.
    heal = auto()
    # Can be copied by Mirror Move.
    mirror = auto()
    # Unknown effect.
    mystery = auto()
    # Prevented from being executed or selected in a Sky Battle.
    nonsky = auto()
    # Has no effect on Grass-type Pokemon, Pokemon with the Ability Overcoat, and Pokemon holding Safety Goggles.
    powder = auto()
    # Blocked by Detect, Protect, Spiky Shield, and if not a Status move, King's Shield.
    protect = auto()
    # Power is multiplied by 1.5 when used by a Pokemon with the Ability Mega Launcher.
    pulse = auto()
    #  Power is multiplied by 1.2 when used by a Pokemon with the Ability Iron Fist.
    punch = auto()
    # If this move is successful, the user must recharge on the following turn and cannot make a move.
    recharge = auto()
    # Bounced back to the original user by Magic Coat or the Ability Magic Bounce.
    reflectable = auto()
    # Can be stolen from the original user and instead used by another Pokemon using Snatch.
    snatch = auto()
    # Has no effect on Pokemon with the Ability Soundproof.
    sound = auto()


class Move(Entity):
    """
    Represents data representing an individual move.
    """

    def __init__(self, move_json, pokemon):
        # Example move object:
        # {
        #    'move':'Flash Cannon',
        #    'id':'flashcannon',
        #    'pp':16,
        #    'maxpp':16,
        #    'target':'normal',
        #    'disabled':False
        # }

        self.pokemon = pokemon

        self.id = move_json['id']
        self.id = str.replace(self.id, "60", "")

        # Grab move data
        if self.id == "return102":
            self.id = "return"
        move = json_loader.get_move(self.id)

        # Load and populate entity data
        super().__init__(move)
        
        # Load from given JSON
        try:
            self.current_pp = move_json['pp']
            self.max_pp = move_json['maxpp']
            self.disabled = move_json['disabled']
        except KeyError:
            self.current_pp = self.pp
            self.max_pp = self.pp
            self.disabled = False
        
        self.ignore_negative_offensive = False
        self.ignore_positive_defensive = False
        self.z_broke_protect = False

    def from_json(self, move_dict : dict):
        super().from_json(move_dict)

        try:
            our_flags = move_dict['flags']
            self.flags = MoveFlag.none
            for flag in our_flags:
                # Add the flag to our list of flags
                # Python is so magical <3
                self.flags = self.flags | MoveFlag[flag]
        except KeyError:
            pass

        try:
            self.pp = move_dict['pp']
        except KeyError:
            self.pp = 0

        try:
            # Any boosts that get applied to THIS Pokemon, if any
            # Format: {"atk":1,"def":1,"spa":1,"spd":1,"spe":1} -- raises all stats by 1
            # Stats that won't get boosted are not listed
            self.boosts = move_dict['boosts']
        except KeyError:
            self.boosts = None

        try:
            # "Status", "Special", "Physical"
            self.category = move_dict['category']
        except KeyError:
            self.category = None

        try:
            # How the defender should take this move (i.e. Psyshock is a special move that does physical damage)
            self.defensive_category = move_dict['defensiveCategory']
        except KeyError:
            # If not defined, the defensive category matches the "normal" category
            self.defensive_category = self.category

        try:
            # The type of this move
            self.type = move_dict['type']
        except KeyError:
            self.type = None

        try:
            # Any secondary effects that happen after this move happens.
            # Format: {"chance":10,"self":{"boosts":{"atk":1,"def":1,"spa":1,"spd":1,"spe":1}}}
            self.secondary = move_dict['secondary']
        except KeyError:
            self.secondary = None

        try:
            # The target of this move
            self.target = move_dict['target']
        except KeyError:
            self.target = None

        try:
            # Should this move hit things which would normally be immune?
            # This can be a bool or a list of types it hits.
            can_ignore_immunity = move_dict['ignoreImmunity']
            if type(can_ignore_immunity) is not dict:
                self.ignore_immunity = can_ignore_immunity
            else:
                self.ignore_immunity = True
        except KeyError:
            self.ignore_immunity = False

        try:
            # The base power of this move
            self.base_power = move_dict['basePower']
        except KeyError:
            self.base_power = 0

        try:
            damage_type = move_dict['damage']
            self.does_damage_based_on_level = damage_type == "level"
            try:
                self.constant_damage_amount = int(damage_type)
            except ValueError:
                self.constant_damage_amount = 0
        except KeyError:
            self.does_damage_based_on_level = False
            self.constant_damage_amount = 0

        try:
            # Range of how many times this move will hit, i.e. [2, 5]
            self.multihit = move_dict['multihit']
        except KeyError:
            self.multihit = []

        try:
            # Any extra effects that happen after this move is used
            # For example, Aqua Ring heals the user's HP every turn
            # Format: {"onResidualOrder":6}
            self.effect = move_dict['effect']
        except KeyError:
            self.effect = None

        try:
            # The accuracy of the move
            our_accuracy = int(move_dict['accuracy'])
            if our_accuracy is 1:
                # Accuracy can be listed as "True" sometimes (meaning the move will never miss)
                our_accuracy = 101
            self.accuracy = our_accuracy
        except KeyError:
            self.accuracy = 0

        try:
            # The priority of this move.
            # 0 means "normal" priority
            self.priority = move_dict['priority']
        except KeyError:
            self.priority = 0

        try:
            self.one_hit_ko = move_dict['ohko']
        except KeyError:
            self.one_hit_ko = False

        try:
            self.critical_hit_ratio = move_dict['critRatio']
        except KeyError:
            self.critical_hit_ratio = 1

        try:
            self.will_crit = move_dict['willCrit']
        except KeyError:
            self.will_crit = False

        try:
            self.crit_modifier = move_dict['critModifier']
        except KeyError:
            self.crit_modifier = 1.5

        try:
            self.use_defender_offensive_stat = move_dict['useTargetOffensive']
        except KeyError:
            self.use_defender_offensive_stat = False

        try:
            self.use_attacker_defense_stat = move_dict['useSourceDefensive']
        except KeyError:
            self.use_attacker_defense_stat = False

        try:
            # Any extra volatile status, like Substitutes
            # Format: "Substitute", "partiallytrapped", etc.
            self.volatile_status = move_dict['volatileStatus']
        except KeyError:
            self.volatile_status = None

        try:
            if move_dict['isZ'] is not "":
                self.is_z_move = True
            else:
                self.is_z_move = False
        except KeyError:
            self.is_z_move = False

        try:
            self.z_move_power = move_dict['zMovePower']
        except KeyError:
            self.z_move_power = 0

        try:
            self.z_move_boost = move_dict['zMoveBoost']
        except KeyError:
            self.z_move_boost = None

        try:
            self.ignore_defensive = move_dict['ignoreDefensive']
        except KeyError:
            self.ignore_defensive = False

        try:
            self.ignore_offensive = move_dict['ignoreOffensive']
        except KeyError:
            self.ignore_offensive = False

    def __str__(self):
        output = self.name
        if self.disabled:
            output += " (Disabled)"
        output += "\n" + str(self.pp) + "/" + str(self.max_pp) + " PP"
        return output