#!/usr/bin/env python3

import src.geniusect.config as config

from poke_env.player_configuration import PlayerConfiguration
from poke_env.server_configuration import ShowdownServerConfiguration

from src.geniusect.player.reinforcement_learning_player import RLPlayer

if __name__ == "__main__":
    if config.get_train_against_ladder():
        server_configuration=ShowdownServerConfiguration
        validate = False
    else:
        server_configuration = None
        validate = True

    env_player = RLPlayer(battle_format="gen8randombattle",
        avatar=120,
        train=True,
        validate=validate,
        load_from_checkpoint=config.get_load_from_checkpoint(),
        player_configuration=PlayerConfiguration(config.get_bot_username(), config.get_bot_password()),
        server_configuration=server_configuration)
