#!/usr/bin/env python3

import logging
import threading
def start_showdown(**kwargs):    
    try:
        import subprocess
        print("Starting local Showdown server")
        subprocess.run(["node", "Pokemon-Showdown/pokemon-showdown"])
    except FileNotFoundError:
        pass

import src.geniusect.config as config

from poke_env.player_configuration import PlayerConfiguration
from poke_env.server_configuration import ShowdownServerConfiguration

from src.geniusect.player.reinforcement_learning_player import RLPlayer


if __name__ == "__main__":
    if config.get_train_against_ladder():
        server_configuration=ShowdownServerConfiguration
        validate = False
        log_level = logging.INFO
    else:
        thread = threading.Thread(target=start_showdown)
        thread.start()
        server_configuration = None
        validate = True
        log_level = logging.WARNING

    env_player = RLPlayer(battle_format="gen8randombattle",
        avatar=120,
        train=True,
        validate=validate,
        log_level=log_level,
        load_from_checkpoint=config.get_load_from_checkpoint(),
        player_configuration=PlayerConfiguration(config.get_bot_username(), config.get_bot_password()),
        server_configuration=server_configuration)
