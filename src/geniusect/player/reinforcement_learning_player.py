#!/usr/bin/env python3

import numpy as np
import tensorflow as tf

import src.geniusect.config as config

from rl.agents.dqn import DQNAgent
from rl.policy import LinearAnnealedPolicy, EpsGreedyQPolicy
from rl.memory import SequentialMemory
from tensorflow.keras.layers import Dense, Flatten
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.optimizers import Adam

from typing import Any, Callable, List, Optional, Tuple, Union, Set

from poke_env.data import ABILITYDEX, to_id_str
from poke_env.environment.battle import Battle
from poke_env.environment.effect import Effect
from poke_env.environment.field import Field
from poke_env.environment.pokemon import Pokemon
from poke_env.environment.pokemon_type import PokemonType
from poke_env.environment.side_condition import SideCondition
from poke_env.environment.status import Status
from poke_env.player.env_player import Gen8EnvSinglePlayer
from poke_env.player.random_player import RandomPlayer
from poke_env.player_configuration import PlayerConfiguration
from poke_env.server_configuration import ServerConfiguration
from poke_env.teambuilder.teambuilder import Teambuilder
from poke_env.environment.weather import Weather

from src.geniusect.player.max_damage_player import MaxDamagePlayer

AVAILABLE_STATS = ["atk", "def", "spa", "spd", "spe", "evasion"]
NUM_MOVES = 4

tf.random.set_seed(0)
np.random.seed(0)

class RLPlayer(Gen8EnvSinglePlayer):
    def __init__(
        self,
        player_configuration: Optional[PlayerConfiguration] = None,
        *,
        avatar: Optional[int] = None,
        battle_format: str = "gen8randombattle",
        log_level: Optional[int] = None,
        server_configuration: Optional[ServerConfiguration] = None,
        start_listening: bool = True,
        team: Optional[Union[str, Teambuilder]] = None,
    ):
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
        super(RLPlayer, self).__init__(
            player_configuration=player_configuration,
            avatar=avatar,
            battle_format=battle_format,
            log_level=log_level,
            server_configuration=server_configuration,
            start_listening=start_listening,
            team=team,
        )

        # Output dimension
        n_action = len(self.action_space)

        self.model = Sequential()
        self.model.add(Dense(128, name="First_Layer", activation="elu", input_shape=(1, self.get_layer_size())))

        # Our embedding have shape (1, 10), which affects our hidden layer
        # dimension and output dimension
        # Flattening resolve potential issues that would arise otherwise
        self.model.add(Flatten(name="Flatten_Layer"))
        self.model.add(Dense(n_action, name="Second_Layer", activation="elu"))
        self.model.add(Dense(n_action, name="Final_Layer", activation="linear"))

        memory = SequentialMemory(limit=config.get_num_training_steps(), window_length=1)

        # Simple epsilon greedy
        policy = LinearAnnealedPolicy(
            EpsGreedyQPolicy(),
            attr="eps",
            value_max=1.0,
            value_min=0.05,
            value_test=0,
            nb_steps=config.get_num_training_steps(),
        )

        # Defining our DQN
        self.dqn = DQNAgent(
            model=self.model,
            nb_actions=n_action,
            policy=policy,
            memory=memory,
            nb_steps_warmup=1000,
            gamma=0.5,
            target_model_update=1,
            delta_clip=0.01,
            enable_double_dqn=True,
        )

        self.dqn.compile(Adam(lr=0.00025), metrics=["mae"])

        self.seen_abilities = {}

    async def _battle_started_callback(self, battle : Battle) -> None:
        await self._send_message("/timer on", battle.battle_tag)
        await self._send_message("I'm a bot! I'm probably going to crash and forfeit at some point, so be nice!", battle.battle_tag)

    def embed_battle(self, battle):
        our_active_pokemon = battle.active_pokemon
        opponent_active_pokemon = battle.opponent_active_pokemon

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
                    opponent_active_pokemon.type_1,
                    opponent_active_pokemon.type_2,
                )

            start_boost_index = i * len(AVAILABLE_STATS)

            move_boosts = move.boosts
            if move_boosts:
                for j in range(len(AVAILABLE_STATS)):
                    current_index = start_boost_index + j
                    try:
                        moves_all_boosts[current_index] = move_boosts[AVAILABLE_STATS[j]] / 6
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
                        moves_all_boosts[current_index] += (secondary_boosts[AVAILABLE_STATS[j]] / 6) * chance
                    except (KeyError, UnboundLocalError):
                        pass

        # We count how many pokemons have not fainted in each team
        remaining_mon_team = (
            len([mon for mon in battle.team.values() if mon.fainted]) / 6
        )
        remaining_mon_opponent = (
            len([mon for mon in battle.opponent_team.values() if mon.fainted]) / 6
        )

        our_side_conditions = self._side_condition_id(battle.side_conditions)
        opponent_side_conditions = self._side_condition_id(battle.opponent_side_conditions)

        weather = battle.weather
        if weather is None:
            weather = -1.0
        else:
            weather = weather / len(Weather)

        field_set = battle.fields
        field_id = 0.0

        for field in field_set:
            field_bit = 1 << int(field)
            field_id += field_bit

        field_id = field_id / (1 << len(Field))

        our_dynamax_turns_left = battle.dynamax_turns_left
        if our_dynamax_turns_left is None:
            our_dynamax_turns_left = -1.0
        else:
            our_dynamax_turns_left = our_dynamax_turns_left / 3.0

        opponent_dynamax_turns_left = battle.opponent_dynamax_turns_left
        if opponent_dynamax_turns_left is None:
            opponent_dynamax_turns_left = -1.0
        else:
            opponent_dynamax_turns_left = opponent_dynamax_turns_left / 3.0

        if battle.can_dynamax:
            our_dynamax_status = 1.0
        else:
            our_dynamax_status = 0.0

        if battle.opponent_can_dynamax:
            opponent_dynamax_status = 1.0
        else:
            opponent_dynamax_status = 0.0
        
        if battle.can_mega_evolve:
            our_mega_evolve_status = 1.0
        else:
            our_mega_evolve_status = 0.0
        
        if battle.can_z_move:
            our_z_move_status = 1.0
        else:
            our_z_move_status = 0.0

        our_pokemon_type_1 = int(our_active_pokemon.type_1) / len(PokemonType)
        if our_active_pokemon.type_2 is None:
            our_pokemon_type_2 = -1.0
        else:
            our_pokemon_type_2 = int(our_active_pokemon.type_2) / len(PokemonType)

        opponent_pokemon_type_1 = int(opponent_active_pokemon.type_1) / len(PokemonType)
        if opponent_active_pokemon.type_2 is None:
            opponent_pokemon_type_2 = -1.0
        else:
            opponent_pokemon_type_2 = int(opponent_active_pokemon.type_2) / len(PokemonType)

        our_base_stats = np.ones(len(AVAILABLE_STATS))
        opponent_base_stats = np.ones(len(AVAILABLE_STATS))

        for i in range(len(AVAILABLE_STATS)):
            stat = AVAILABLE_STATS[i]

            # Correct evasion to HP
            if stat == "evasion":
                stat = "hp"

            our_base_stats[i] = our_active_pokemon.base_stats[stat] / 255
            opponent_base_stats[i] = opponent_active_pokemon.base_stats[stat] / 255

        our_active_boosts = np.zeros(len(AVAILABLE_STATS))
        opponent_active_boosts = np.zeros(len(AVAILABLE_STATS))

        for i in range(len(AVAILABLE_STATS)):
            stat = AVAILABLE_STATS[i]
            try:
                our_active_boosts[i] = our_active_pokemon.boosts[stat] / 6
            except KeyError:
                pass
            try:
                opponent_active_boosts[i] = opponent_active_pokemon.boosts[stat] / 6
            except KeyError:
                pass

        our_status = np.negative(np.ones(6))
        opponent_status = np.negative(np.ones(6))

        status_index = 0
        for mon in battle.team:
            pkm = battle.team[mon]
            if pkm.status is None:
                our_status[status_index] = -1
            else:
                our_status[status_index] = int(pkm.status) / len(Status)
            status_index += 1

        status_index = 0
        for mon in battle.opponent_team:
            pkm = battle.opponent_team[mon]
            if pkm.status is None:
                opponent_status[status_index] = -1
            else:
                opponent_status[status_index] = int(pkm.status) / len(Status)
            status_index += 1

        our_effects = np.zeros(len(Effect))
        opponent_effects = np.zeros(len(Effect))

        effect_index = 0
        for effect in Effect:
            if effect in our_active_pokemon.effects:
                our_effects[effect_index] = 1
            if effect in opponent_active_pokemon.effects:
                opponent_effects[effect_index] = 1
            effect_index += 1

        if our_active_pokemon.ability is not None:
            our_ability = ABILITYDEX[to_id_str(our_active_pokemon.ability)]
            our_ability = our_ability / len(ABILITYDEX)
        else:
            our_ability = -1

        if opponent_active_pokemon.ability is not None:
            opponent_ability = ABILITYDEX[to_id_str(opponent_active_pokemon.ability)]
            opponent_ability = opponent_ability / len(ABILITYDEX)
        else:
            opponent_ability = -1

        final_vector = np.concatenate(
            [
                moves_base_power,
                moves_dmg_multiplier,
                moves_all_boosts,
                our_base_stats,
                opponent_base_stats,
                our_active_boosts,
                opponent_active_boosts,
                our_effects,
                opponent_effects,
                our_status,
                opponent_status,
                [our_active_pokemon.current_hp_fraction, opponent_active_pokemon.current_hp_fraction],
                [remaining_mon_team, remaining_mon_opponent],
                [our_side_conditions, opponent_side_conditions],
                [weather, field_id],
                [our_dynamax_status, opponent_dynamax_status, our_dynamax_turns_left, opponent_dynamax_turns_left],
                [our_mega_evolve_status, our_z_move_status],
                [our_pokemon_type_1, our_pokemon_type_2],
                [opponent_pokemon_type_1, opponent_pokemon_type_2],
                [our_ability, opponent_ability]
            ]
        )

        return final_vector

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
        return 32 + NUM_MOVES + NUM_MOVES + (NUM_MOVES * len(AVAILABLE_STATS)) + len(AVAILABLE_STATS) + len(AVAILABLE_STATS) + len(AVAILABLE_STATS) + len(AVAILABLE_STATS) + len(Effect) + len(Effect)

    def get_model(self) -> Model:
        return self.model

    def get_dqn(self) -> DQNAgent:
        return self.dqn

    def dqn_evaluation(self, player, dqn, nb_episodes):
        # Reset battle statistics
        player.reset_battles()
        dqn.test(player, nb_episodes=nb_episodes, visualize=False, verbose=False)

        print(
            "DQN Evaluation: %d victories out of %d episodes"
            % (player.n_won_battles, nb_episodes)
        )

    def evaluate_dqn(self) -> None:
        opponent = RandomPlayer(battle_format="gen8randombattle")
        second_opponent = MaxDamagePlayer(battle_format="gen8randombattle")
        
        # Evaluation
        print("Results against random player:")
        self.play_against(
            env_algorithm=self.dqn_evaluation,
            opponent=opponent,
            env_algorithm_kwargs={"dqn": self.dqn, "nb_episodes": config.get_num_evaluation_episodes()},
        )

        print("\nResults against max player:")
        self.play_against(
            env_algorithm=self.dqn_evaluation,
            opponent=second_opponent,
            env_algorithm_kwargs={"dqn": self.dqn, "nb_episodes": config.get_num_evaluation_episodes()},
        )

    def _side_condition_id(self, side_conditions : Set[SideCondition]) -> float:
        output = 0.0

        for condition in side_conditions:
            condition_bit = 1 << int(condition)
            output += condition_bit

        return output / (1 << len(SideCondition))

        