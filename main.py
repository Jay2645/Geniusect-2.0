#!/usr/bin/env python3

import asyncio
import src.geniusect.config as config

from poke_env.player_configuration import PlayerConfiguration
from poke_env.server_configuration import ShowdownServerConfiguration
from poke_env.player.random_player import RandomPlayer

from src.geniusect.player.reinforcement_learning_player import RLPlayer
from src.geniusect.player.max_damage_player import MaxDamagePlayer

# This is the function that will be used to train the dqn
def dqn_training(player, dqn, nb_steps):
    dqn.fit(player, nb_steps=nb_steps)
    player.complete_current_battle()

if __name__ == "__main__":
    print("Creating players")

    env_player = RLPlayer(battle_format="gen8randombattle")#, 
#        player_configuration=PlayerConfiguration(config.get_bot_username(), config.get_bot_password()),
#        server_configuration=ShowdownServerConfiguration)

    opponent = MaxDamagePlayer(battle_format="gen8randombattle")

    nb_steps = config.get_num_training_steps()

    print("Beginning training with " + str(nb_steps) + " steps")
    
    # Training
    env_player.play_against(
        env_algorithm=dqn_training,
        opponent=opponent,
        env_algorithm_kwargs={"dqn": env_player.dqn, "nb_steps": nb_steps},
    )

    print("Training complete")

    env_player.evaluate_dqn()
