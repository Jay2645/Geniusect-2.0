#!/usr/bin/env python3

import asyncio
import src.geniusect.config as config

from poke_env.player.random_player import RandomPlayer
from poke_env.player_configuration import PlayerConfiguration
from poke_env.server_configuration import ShowdownServerConfiguration


async def main():
    # We create a random player
    player = RandomPlayer(
        player_configuration=PlayerConfiguration(config.get_bot_username(), config.get_bot_password()),
        server_configuration=ShowdownServerConfiguration
    )

    await player.send_challenges(config.get_human_username(), n_challenges=1)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
