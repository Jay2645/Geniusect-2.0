#!/usr/bin/env python3

import numpy as np

from typing import List

from poke_env.environment.battle import Battle
from poke_env.player.env_player import Gen8EnvSinglePlayer

import src.geniusect.config as config

AVAILABLE_STATS = ["atk", "def", "spa", "spd", "spe", "evasion"]
NUM_MOVES = 4

class RLPlayer(Gen8EnvSinglePlayer):
    async def _battle_started_callback(self, battle : Battle) -> None:
        await self._send_message("/timer on", battle.battle_tag)
        await self._send_message("I'm a bot! I'm probably going to crash and forfeit at some point, so be nice!", battle.battle_tag)

    def embed_battle(self, battle):
        # -1 indicates that the move does not have a base power
        # or is not available
        moves_base_power = -np.ones(NUM_MOVES)
        moves_dmg_multiplier = np.ones(NUM_MOVES)

        moves_all_boosts = np.zeros(NUM_MOVES * len(AVAILABLE_STATS))
        
        for i, move in enumerate(battle.available_moves):
            moves_base_power[i] = (
                move.base_power / 100
            )  # Simple rescaling to facilitate learning

            if move.type:
                moves_dmg_multiplier[i] = move.type.damage_multiplier(
                    battle.opponent_active_pokemon.type_1,
                    battle.opponent_active_pokemon.type_2,
                )

            start_boost_index = i * len(AVAILABLE_STATS)

            move_boosts = move.boosts
            if move_boosts:
                for j in range(len(AVAILABLE_STATS)):
                    current_index = start_boost_index + j
                    try:
                        moves_all_boosts[current_index] = move_boosts[AVAILABLE_STATS[j]] / 4
                    except KeyError:
                        pass

            secondary_effects = move.secondary
            for effect in secondary_effects:
                try:
                    chance = effect["chance"] / 100
                    secondary_boosts = effect["boosts"]
                except KeyError:
                    pass

                for j in range(len(AVAILABLE_STATS)):
                    current_index = start_boost_index + j
                    try:
                        moves_all_boosts[current_index] += (secondary_boosts[AVAILABLE_STATS[j]] / 4) * chance
                    except (KeyError, UnboundLocalError):
                        pass

        # We count how many pokemons have not fainted in each team
        remaining_mon_team = (
            len([mon for mon in battle.team.values() if mon.fainted]) / 6
        )
        remaining_mon_opponent = (
            len([mon for mon in battle.opponent_team.values() if mon.fainted]) / 6
        )

        # Final vector
        return np.concatenate(
            [
                moves_base_power,
                moves_dmg_multiplier,
                moves_all_boosts,
                [remaining_mon_team, remaining_mon_opponent],
            ]
        )

    def compute_reward(self, battle) -> float:
        return self.reward_computing_helper(
            battle,
            fainted_value = config.get_fainted_reward(),
            hp_value = config.get_hp_reward(),
            starting_value = config.get_starting_value(),
            status_value = config.get_status_value(),
            victory_value = config.get_victory_value()
        )

    def get_layer_size(self) -> int:
        return 2 + NUM_MOVES + NUM_MOVES + (NUM_MOVES * len(AVAILABLE_STATS))