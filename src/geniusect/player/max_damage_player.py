#!/usr/bin/env python3

import random

from poke_env.environment.battle import Battle
from poke_env.environment.move_category import MoveCategory
from poke_env.player.random_player import RandomPlayer
from poke_env.player_configuration import PlayerConfiguration
from poke_env.server_configuration import ServerConfiguration
from poke_env.teambuilder.teambuilder import Teambuilder

import src.geniusect.config as config

from typing import Any, Callable, List, Optional, Tuple, Union, Set

class MaxDamagePlayer(RandomPlayer):
    def __init__(
        self,
        player_configuration: Optional[PlayerConfiguration] = None,
        *,
        battle_format: str = "gen8randombattle",
        log_level: Optional[int] = None,
        max_concurrent_battles: int = 1,
        server_configuration: Optional[ServerConfiguration] = None,
        start_listening: bool = True,
        team: Optional[Union[str, Teambuilder]] = None,
    ) -> None:
        """
        :param player_configuration: Player configuration. If empty, defaults to an
            automatically generated username with no password. This option must be set
            if the server configuration requires authentication.
        :type player_configuration: PlayerConfiguration, optional
        :param avatar: Player avatar id. Optional.
        :type avatar: int, optional
        :param battle_format: Name of the battle format this player plays. Defaults to
            gen8randombattle.
        :type battle_format: str
        :param log_level: The player's logger level.
        :type log_level: int. Defaults to logging's default level.
        :param max_concurrent_battles: Maximum number of battles this player will play
            concurrently. If 0, no limit will be applied. Defaults to 1.
        :type max_concurrent_battles: int
        :param server_configuration: Server configuration. Defaults to Localhost Server
            Configuration.
        :type server_configuration: ServerConfiguration, optional
        :param start_listening: Wheter to start listening to the server. Defaults to
            True.
        :type start_listening: bool
        :param team: The team to use for formats requiring a team. Can be a showdown
            team string, a showdown packed team string, of a ShowdownTeam object.
            Defaults to None.
        :type team: str or Teambuilder, optional
        """
        super(MaxDamagePlayer, self).__init__(
            player_configuration=player_configuration,
            avatar=58,
            log_level=log_level,
            server_configuration=server_configuration,
            start_listening=start_listening,
        )

        self._tryhard_percent = config.get_starting_tryhard()
        self._tryhard_floor = config.get_tryhard_floor()
    
    async def _battle_started_callback(self, battle : Battle) -> None:
        await self._send_message("Tryhard percent: " + str(self._tryhard_percent), battle.battle_tag)

    async def _battle_finished_callback(self, battle: Battle) -> None:
        if battle.won:
            if self._tryhard_percent > self._tryhard_floor:
                self._tryhard_percent -= 0.01
        else:
            if self._tryhard_percent < 1.0:
                self._tryhard_percent += 0.01

    def choose_move(self, battle):
        # If the player can attack, it will
        random_num = random.random()
        if battle.available_moves and random_num < self._tryhard_percent:
            our_pokemon = battle.active_pokemon
            boosts = our_pokemon.boosts

            opponent_pkm = battle.opponent_active_pokemon
            
            best_power = -1
            best_move = battle.available_moves[0]
            for move in battle.available_moves:
                move_category = move.category

                if move_category == MoveCategory.PHYSICAL:
                    current_boosts = boosts["atk"]
                elif move_category == MoveCategory.SPECIAL:
                    current_boosts = boosts["spa"]
                else:
                    current_boosts = 0

                if current_boosts >= 0:
                    current_boosts = (current_boosts + 2) / 2
                else:
                    current_boosts = 2 / ((-current_boosts) + 2)

                dmg_multiplier = 1
                stab = 1
                if move.type:
                    dmg_multiplier = move.type.damage_multiplier(
                        opponent_pkm.type_1,
                        opponent_pkm.type_2,
                    )
                    if move.type == our_pokemon.type_1 or move.type == our_pokemon.type_2:
                        stab = 1.5
                
                scaled_power = dmg_multiplier * move.base_power * current_boosts * move.accuracy * stab
                if scaled_power > best_power:
                    best_power = scaled_power
                    best_move = move

            if best_power > 30:
                # Finds the best move among available ones
                return self.create_order(best_move)
        
        return self.choose_random_move(battle)
			