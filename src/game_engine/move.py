#!/usr/bin/env python3

from src.game_engine.effects import Entity

class Move(Entity):
    def __init__(self, move_json):
        # Example move object:
        # {
        #    'move':'Flash Cannon',
        #    'id':'flashcannon',
        #    'pp':16,
        #    'maxpp':16,
        #    'target':'normal',
        #    'disabled':False
        # }

        self.id = move_json['id']
        
        # Load from given JSON
        try:
            self.current_pp = move_json['pp']
            self.max_pp = move_json['maxpp']
            self.disabled = move_json['disabled']
        except KeyError:
            self.disabled = False
        
        # Grab move data
        from src.io_process.showdown import Showdown
        login = Showdown()
        movedex = login.moves[self.id]

        # Load and populate entity data
        super().__init__(movedex)

        self.ignore_negative_offensive = False
        self.ignore_positive_defensive = False
        self.z_broke_protect = False

    def from_json(self, movedex):
        super().from_json(movedex)

        try:
            self.pp = movedex['pp']
        except KeyError:
            self.pp = 0

        try:
            # Any boosts that get applied to THIS Pokemon, if any
            # Format: {"atk":1,"def":1,"spa":1,"spd":1,"spe":1} -- raises all stats by 1
            # Stats that won't get boosted are not listed
            self.boosts = movedex['boosts']
        except KeyError:
            self.boosts = None

        try:
            # "Status", "Special", "Physical"
            self.category = movedex['category']
        except KeyError:
            self.category = None

        try:
            # How the defender should take this move (i.e. Psyshock is a special move that does physical damage)
            self.defensive_category = movedex['defensiveCategory']
        except KeyError:
            # If not defined, the defensive category matches the "normal" category
            self.defensive_category = self.category

        try:
            # The type of this move
            self.type = movedex['type']
        except KeyError:
            self.type = None

        try:
            # Any secondary effects that happen after this move happens.
            # Format: {"chance":10,"self":{"boosts":{"atk":1,"def":1,"spa":1,"spd":1,"spe":1}}}
            self.secondary = movedex['secondary']
        except KeyError:
            self.secondary = None

        try:
            # The target of this move
            self.target = movedex['target']
        except KeyError:
            self.target = None

        try:
            # Should this move hit things which would normally be immune?
            # This can be a bool or a list of types it hits.
            can_ignore_immunity = movedex['ignoreImmunity']
            if type(can_ignore_immunity) is not dict:
                self.ignore_immunity = can_ignore_immunity
            else:
                self.ignore_immunity = True
        except KeyError:
            self.ignore_immunity = False

        try:
            # The base power of this move
            self.base_power = movedex['basePower']
        except KeyError:
            self.base_power = 0

        try:
            damage_type = movedex['damage']
            self.does_damage_based_on_level = damage_type is "level"
            try:
                self.constant_damage_amount = int(damage_type)
            except TypeError:
                self.set_damage_amount = 0
        except KeyError:
            self.does_damage_based_on_level = False
            self.constant_damage_amount = 0

        try:
            # Range of how many times this move will hit, i.e. [2, 5]
            self.multihit = movedex['multihit']
        except KeyError:
            self.multihit = []

        try:
            # Any extra effects that happen after this move is used
            # For example, Aqua Ring heals the user's HP every turn
            # Format: {"onResidualOrder":6}
            self.effect = movedex['effect']
        except KeyError:
            self.effect = None

        try:
            # The accuracy of the move
            our_accuracy = int(movedex['accuracy'])
            if our_accuracy is 1:
                # Accuracy can be listed as "True" sometimes (meaning the move will never miss)
                our_accuracy = 101
            self.accuracy = our_accuracy
        except KeyError:
            self.accuracy = 0

        try:
            # The priority of this move.
            # 0 means "normal" priority
            self.priority = movedex['priority']
        except KeyError:
            self.priority = 0

        try:
            self.one_hit_ko = movedex['ohko']
        except KeyError:
            self.one_hit_ko = False

        try:
            self.critical_hit_ratio = movedex['critRatio']
        except KeyError:
            self.critical_hit_ratio = 1

        try:
            self.will_crit = movedex['willCrit']
        except KeyError:
            self.will_crit = False

        try:
            self.crit_modifier = movedex['critModifier']
        except KeyError:
            self.crit_modifier = 1.5

        try:
            self.use_defender_offensive_stat = movedex['useTargetOffensive']
        except KeyError:
            self.use_defender_offensive_stat = False

        try:
            self.use_attacker_defense_stat = movedex['useSourceDefensive']
        except KeyError:
            self.use_attacker_defense_stat = False

        try:
            # Any extra volatile status, like Substitutes
            # Format: "Substitute", "partiallytrapped", etc.
            self.volatile_status = movedex['volatileStatus']
        except KeyError:
            self.volatile_status = None

        try:
            if movedex['isZ'] is not "":
                self.is_z_move = True
            else:
                self.is_z_move = False
        except KeyError:
            self.is_z_move = False

        try:
            self.z_move_power = movedex['zMovePower']
        except KeyError:
            self.z_move_power = 0

        try:
            self.z_move_boost = movedex['zMoveBoost']
        except KeyError:
            self.z_move_boost = None

        try:
            self.ignore_defensive = movedex['ignoreDefensive']
        except KeyError:
            self.ignore_defensive = False

        try:
            self.ignore_offensive = movedex['ignoreOffensive']
        except KeyError:
            self.ignore_offensive = False