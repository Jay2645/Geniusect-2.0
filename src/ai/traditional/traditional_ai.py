#!/usr/bin/env python3

from src.ai.ai import AI
from src.ai.traditional.move_efficiency import effi_move, effi_boost, effi_pkm
from src.game_engine.battle import Battle
from src.game_engine.game_calcs import get_effectiveness
from src.helpers import player_id_to_index, get_enemy_id_from_player_id

class TraditionalAI(AI):
    def __init__(self):
        pass

    def make_best_order(self, battle : Battle, form=None):
        """
        Parse battle.bot_team to find the best pokemon based on his damages against enemy team.
        :param battle: Battle object, current battle.
        :param form: Battle format.
        :return: List of pokemon in bot_team sorted by efficiency ([[1, 6], [-oo, +oo]]).
        """
        team = battle.teams[player_id_to_index(battle.player_id)]
        enemy_team = battle.teams[get_enemy_id_from_player_id(battle.player_id)]
        ordered_team = []
        for i, pokemon in enumerate(team.pokemon):
            average_efficiency = 0
            for enemy_pkm in enemy_team.pokemon:
                pkm_efficiency = -1024
                if form == 'gen7challengecup1v1':
                    for move in pokemon.moves:
                        dmg = effi_move(battle, move, pokemon, enemy_pkm, team)
                        if pkm_efficiency < dmg:
                            pkm_efficiency = dmg
                elif form in ["gen6battlefactory", "gen7bssfactory"]:
                    pkm_efficiency = effi_pkm(battle, pokemon, enemy_pkm)
                average_efficiency += pkm_efficiency
            average_efficiency /= 6
            ordered_team.append([i + 1, average_efficiency])
            ordered_team.sort(key=lambda x: x[1], reverse=True)
        return ordered_team


    def _make_best_switch(self, battle : Battle, force_switch : bool):
        """
        Parse battle.bot_team to find the best pokemon based on his efficiency against current enemy pokemon.
        :param battle: Battle object, current battle.
        :return: (Index of pokemon in bot_team (Integer, [-1, 6]), efficiency (Integer, [0, +oo[))
        """
        if battle.is_trapped:
            return None, -1024

        print("Looking at our best options to switch")
        team = battle.teams[player_id_to_index(battle.player_id)]
        enemy_pkm = battle.teams[get_enemy_id_from_player_id(battle.player_id)].active()
        best_pkm = None
        effi = -1024
        for pokemon in team.pokemon:
            if pokemon is team.active():
                continue
            elif pokemon.is_fainted():
                continue

            # Entry hazards
            our_effi = effi_pkm(battle, enemy_pkm, pokemon, force_switch)
            if team.entry_hazards["stealth_rock"] == 1:
                effi_mod = get_effectiveness(pokemon.types, "Rock") * 4 # Multiply by 4 so a 4x resist becomes 1
                if effi_mod > 0:
                    our_effi /= effi_mod

            ground_effi = get_effectiveness(pokemon.types, "Ground")
            if ground_effi > 0:
                # Can be affected by ground entry hazards, so let's check if we have any
                if team.entry_hazards["spikes"] > 0:
                    our_effi /= (team.entry_hazards["spikes"] * 1.25)
                if team.entry_hazards["sticky_web"] > 0:
                    our_effi /= 1.25
                if team.entry_hazards["toxic_spikes"] > 0:
                    if "Poison" in pokemon.types:
                        our_effi *= 2 # Poison-types remove Toxic Spikes on entry
                    else:
                        poison_effi = get_effectiveness(pokemon.types, "Poison")
                        if poison_effi > 0:
                            our_effi /= (team.entry_hazards["toxic_spikes"] * 1.25)
            
            print(f"Assigning a weight of {our_effi} to switching to {pokemon.name}")

            if our_effi > effi:
                best_pkm = pokemon
                effi = our_effi
        try:
            print("Our best switch right now is a switch to " + best_pkm.name +", with a weight of " + str(effi))
            return team.pokemon.index(best_pkm) + 1, effi
        except (ValueError, AttributeError):
            return None, -1024


    def _make_best_move(self, battle : Battle):
        """
        Parse attacks of current pokemon and send the most efficient based on previous function
        :param battle: Battle object, current battle.
        :return: (Index of move in pokemon (Integer, [-1, 4]), efficiency (Integer, [0, +oo[))
        """
        if battle.force_switch:
            return None, -1024

        pokemon_moves = battle.current_pkm[0]["moves"]

        pokemon = battle.teams[player_id_to_index(battle.player_id)].active()
        enemy_team = battle.teams[get_enemy_id_from_player_id(battle.player_id)]
        enemy_pkm = enemy_team.active()
        best_move = (None, -1)

        if len(pokemon_moves) == 1:  # Case Outrage, Mania, Phantom Force, etc.
            print("Locked into " + str(pokemon_moves[0]) + "!")
            return 1, 100

        for i, move in enumerate(pokemon.moves):  # Classical parse
            if move.disabled or move.pp <= 0:
                print("Cannot use " + move.name + " as it is disabled!")
                continue
            effi = effi_move(battle, move, pokemon, enemy_pkm, enemy_team)
            if effi > best_move[1]:
                print(move.name +"'s score of " + str(effi) + " is greater than the previous best (" + str(best_move[1]) + ")")
                best_move = (i + 1, effi)

        return best_move


    def make_best_action(self, battle : Battle, must_switch : bool = False, must_move : bool = False):
        """
        Choose best action to do each turn.
        Select best action of bot and enemy pokemon, then best pokemon to switch. And finally, chose if it worth or not to
        switch.
        :param battle: Battle object, current battle.
        :return: (Index of move in pokemon (["move"|"switch"], Integer, [-1, 6]))
        """

        best_enm_atk = 0
        best_bot_atk = 0

        bot_pkm = battle.teams[player_id_to_index(battle.player_id)].active()
        enm_pkm = battle.teams[get_enemy_id_from_player_id(battle.player_id)].active()

        if bot_pkm is None:
            raise RuntimeError("We have no active Pokemon")
        elif enm_pkm is None:
            raise RuntimeError("Cannot find any active enemy Pokemon")
        
        if must_move or not battle.force_switch:
            # Check our valid moves
            best_move = self._make_best_move(battle)
        else:
            best_move = (None, -1024)

        # If we don't have a substitute active, look at our options for switching
        if ((best_move[0] is None or not bot_pkm.substitute) and not battle.is_trapped) or must_switch:
            best_switch = self._make_best_switch(battle, False)
            if battle.current_pkm is None or best_move[0] is None or best_move[1] < best_switch[1]:
                return "switch", best_switch[0]
        return ["move"] + [i for i in best_move]
