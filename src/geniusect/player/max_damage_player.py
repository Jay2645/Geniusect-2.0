#!/usr/bin/env python3

from poke_env.player.random_player import RandomPlayer
from poke_env.player_configuration import PlayerConfiguration
from poke_env.server_configuration import ServerConfiguration
from poke_env.teambuilder.teambuilder import Teambuilder

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

    def choose_move(self, battle):
        # If the player can attack, it will
        if battle.available_moves:
            opponent_pkm = battle.opponent_active_pokemon
            
            best_power = -1
            best_move = battle.available_moves[0]
            for move in battle.available_moves:
                dmg_multiplier = 1
                if move.type:
                    dmg_multiplier = move.type.damage_multiplier(
                        opponent_pkm.type_1,
                        opponent_pkm.type_2,
                    )
                
                scaled_power = dmg_multiplier * move.base_power
                if scaled_power > best_power:
                    best_power = scaled_power
                    best_move = move

            # Finds the best move among available ones
            return self.create_order(best_move)

        # If no attack is available, a random switch will be made
        else:
            return self.choose_random_move(battle)
			