#!/usr/bin/env python3

from abc import ABC, abstractmethod, abstractproperty
from gym.core import Env  # pyre-ignore

from queue import Queue
from threading import Thread

from typing import Any, Callable, List, Optional, Tuple, Union

from rl.agents.dqn import DQNAgent
from rl.callbacks import Callback
from rl.policy import LinearAnnealedPolicy, EpsGreedyQPolicy
from rl.memory import SequentialMemory

from tensorflow.keras.optimizers import Adam
from tensorflow.keras.models import Model

from typing import Any, Callable, List, Optional, Tuple, Union, Set

from poke_env.data import ABILITYDEX, ITEMS
from poke_env.environment.effect import Effect
from poke_env.environment.field import Field
from poke_env.environment.move import Move, EmptyMove
from poke_env.environment.move_category import MoveCategory
from poke_env.environment.pokemon import Pokemon
from poke_env.environment.pokemon_type import PokemonType
from poke_env.environment.side_condition import SideCondition
from poke_env.environment.status import Status
from poke_env.player.random_player import RandomPlayer
from poke_env.environment.weather import Weather
from poke_env.environment.battle import Battle
from poke_env.player.player import Player
from poke_env.player_configuration import PlayerConfiguration
from poke_env.server_configuration import ServerConfiguration
from poke_env.teambuilder.teambuilder import Teambuilder
from poke_env.utils import to_id_str

from src.geniusect.player.max_damage_player import MaxDamagePlayer
from src.geniusect.player.default_player import DefaultPlayer

import asyncio
import os
import threading
import _thread
import time

import numpy as np
import tensorflow as tf

import src.geniusect.config as config

AVAILABLE_STATS = ["atk", "def", "spa", "spd", "spe", "evasion", "accuracy"]
NUM_MOVES = 4
MOVE_MEMORY = 100

tf.random.set_seed(0)
np.random.seed(0)

class Geniusect(Env, ABC, Callback):  # pyre-ignore
    """Player exposing the Open AI Gym Env API. Recommended use is with play_against."""

    _ACTION_SPACE = None
    MAX_BATTLE_SWITCH_RETRY = 10000
    PAUSE_BETWEEN_RETRIES = 0.001

    def __init__(
        self,
        train = True,
        validate = True,
        load_from_checkpoint = False,
    ):
        self._actions = {}
        self._current_battle: Battle
        self._observations = {}
        self._reward_buffer = {}
        self._start_new_battle = False

        input_layer_size = self._get_layer_size()
        output_layer_size = len(self.action_space)
        self.model = config.build_model(input_layer_size, output_layer_size)

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
            nb_actions=output_layer_size,
            policy=policy,
            memory=memory,
            nb_steps_warmup=1000,
            gamma=0.5,
            target_model_update=1,
            delta_clip=0.01,
            enable_double_dqn=True,
        )

        self.dqn.compile(Adam(lr=0.00025), metrics=["mae"])

        self.train = train
        self.use_checkpoint = load_from_checkpoint
        self.validate = validate

        self._timer = None
        self._last_step_start_time = time.time()
        # Only join lobbies on localhost
        self.done_joining_lobby = self.validate and "localhost" not in self._server_url

        self._taken_actions = np.negative(np.ones(MOVE_MEMORY))

        if self.train:
            self._train()

    # Env overrides
    def seed(self, seed=None) -> None:
        """Sets the numpy seed."""
        np.random.seed(seed)

    def step(self, action: int) -> Tuple:
        """Performs action in the current battle.

        :param action: The action to perform.
        :type action: int
        :return: A tuple containing the next observation, the reward, a boolean
            indicating wheter the episode is finished, and additional information
        :rtype: tuple
        """
        if self._current_battle.finished:
            observation = self.reset()
        else:
            self._actions[self._current_battle].put(action)
            observation = self._observations[self._current_battle].get()
        return (
            observation,
            self._compute_reward(self._current_battle),
            self._current_battle.finished,
            {},
        )

    def reset(self) -> Any:
        """Resets the internal environment state. The current battle will be set to an
        active unfinished battle.

        :return: The observation of the new current battle.
        :rtype: Any
        :raies: EnvironmentError
        """
        for _ in range(self.MAX_BATTLE_SWITCH_RETRY):
            battles = dict(self._actions.items())
            battles = [b for b in battles if not b.finished]
            if battles:
                self._current_battle = battles[0]
                observation = self._observations[self._current_battle].get()
                return observation
            time.sleep(self.PAUSE_BETWEEN_RETRIES)
        else:
            raise EnvironmentError("User %s has no active battle." % self.username)

    def render(self, mode="human") -> None:
        """A one line rendering of the current state of the battle."""
        print(
            "  Turn %4d. | [%s][%3d/%3dhp] %10.10s - %10.10s [%3d%%hp][%s]"
            % (
                self._current_battle.turn,
                "".join(
                    [
                        "⦻" if mon.fainted else "●"
                        for mon in self._current_battle.team.values()
                    ]
                ),
                self._current_battle.active_pokemon.current_hp or 0,
                self._current_battle.active_pokemon.max_hp or 0,
                self._current_battle.active_pokemon.species,
                self._current_battle.opponent_active_pokemon.species,  # pyre-ignore
                self._current_battle.opponent_active_pokemon.current_hp  # pyre-ignore
                or 0,
                "".join(
                    [
                        "⦻" if mon.fainted else "●"
                        for mon in self._current_battle.opponent_team.values()
                    ]
                ),
            ),
            end="\n" if self._current_battle.finished else "\r",
        )

    def close(self) -> None:
        """Unimplemented. Has no effect."""

    # Callback overrides
    def on_step_begin(self, step, logs):
        self._last_step_start_time = time.time()

        timeout = config.get_step_timeout()

        self._timer = threading.Timer(timeout, self._step_timeout)
        self._timer.start()

    def on_step_end(self, step, logs):
        self._timer.cancel()
        self._timer = None

    def on_episode_end(self, episode, logs):
        """ Render environment at the end of each action """
        if not self.done_joining_lobby:
            print("")
            self.render(mode='human')

    # Public methods
    @property
    def action_space(self) -> List:
        """The action space for gen 8 single battles.

        The conversion to moves is done as follows:

            0 <= action < 4:
                The actionth available move in battle.available_moves is executed.
            4 <= action < 8:
                The action - 4th available move in battle.available_moves is executed,
                with z-move.
            8 <= action < 12:
                The action - 8th available move in battle.available_moves is executed,
                with mega-evolution.
            12 <= action < 16:
                The action - 12th available move in battle.available_moves is executed,
                while dynamaxing.
            16 <= action < 22
                The action - 16th available switch in battle.available_switches is
                executed.
        """
        return self._ACTION_SPACE


    def on_battle_finished(self, battle: Battle) -> None:
        self._observations[battle].put(self.embed_battle(battle))

    def choose_move(self, battle: Battle) -> str:
        if battle not in self._observations or battle not in self._actions:
            self._init_battle(battle)
        self._observations[battle].put(self.embed_battle(battle))
        action = self._actions[battle].get()

        # Place oldest action at the front of the list (rotating/shifting the list by 1)
        # e.g. 4,3,2,1 -> 1,4,3,2
        self._taken_actions = np.roll(self._taken_actions, 1)

        # Place most recent taken action at index 0
        # e.g. 5,4,3,2
        self._taken_actions[0] = action / len(self._ACTION_SPACE)

        return self._action_to_move(action, battle)

    def play_against(
        self, env_algorithm: Callable, us: Player, opponent: Player, env_algorithm_kwargs=None
    ):
        """Executes a function controlling the player while facing opponent.

        The env_algorithm function is executed with the player environment as first
        argument. It exposes the open ai gym API.

        Additional arguments can be passed to the env_algorithm function with
        env_algorithm_kwargs.

        Battles against opponent will be launched as long as env_algorithm is running.
        When env_algorithm returns, the current active battle will be finished randomly
        if it is not already.

        :param env_algorithm: A function that controls the player. It must accept the
            player as first argument. Additional arguments can be passed with the
            env_algorithm_kwargs argument.
        :type env_algorithm: callable
        :param opponent: A player against with the env player will player.
        :type opponent: Player
        :param env_algorithm_kwargs: Optional arguments to pass to the env_algorithm.
            Defaults to None.
        """
        self._start_new_battle = True

        async def launch_battles(player: Player, opponent: Player):
            if opponent is not None:
                battles_coroutine = asyncio.gather(
                    player.send_challenges(
                        opponent=to_id_str(opponent.username),
                        n_challenges=1,
                        to_wait=opponent.logged_in,
                    ),
                    opponent.accept_challenges(
                        opponent=to_id_str(player.username), n_challenges=1
                    ),
                )
            else:
                battles_coroutine = asyncio.gather(player.ladder(n_games=1))
            await battles_coroutine

        def env_algorithm_wrapper(player, kwargs):
            env_algorithm(player, **kwargs)

            player._start_new_battle = False
            while True:
                try:
                    player.complete_current_battle()
                    player.reset()
                except OSError:
                    break

        loop = asyncio.get_event_loop()

        if env_algorithm_kwargs is None:
            env_algorithm_kwargs = {}

        thread = Thread(
            target=lambda: env_algorithm_wrapper(self, env_algorithm_kwargs)
        )
        thread.start()

        while self._start_new_battle:
            loop.run_until_complete(launch_battles(us, opponent))
        thread.join()

    # Protected methods
    def _action_to_move(self, action: int, battle: Battle) -> str:
        """Converts actions to move orders.

        The conversion is done as follows:

        0 <= action < 4:
            The actionth available move in battle.available_moves is executed.
        4 <= action < 8:
            The action - 4th available move in battle.available_moves is executed, with
            z-move.
        8 <= action < 12:
            The action - 8th available move in battle.available_moves is executed, with
            mega-evolution.
        8 <= action < 12:
            The action - 8th available move in battle.available_moves is executed, with
            mega-evolution.
        12 <= action < 16:
            The action - 12th available move in battle.available_moves is executed,
            while dynamaxing.
        16 <= action < 22
            The action - 16th available switch in battle.available_switches is executed.

        If the proposed action is illegal, a random legal move is performed.

        :param action: The action to convert.
        :type action: int
        :param battle: The battle in which to act.
        :type battle: Battle
        :return: the order to send to the server.
        :rtype: str
        """
        if (
            action < 4
            and action < len(battle.available_moves)
            and not battle.force_switch
        ):
            return self.create_order(battle.available_moves[action])
        elif (
            not battle.force_switch
            and battle.can_z_move
            and 0 <= action - 4 < len(battle.active_pokemon.available_z_moves)
        ):
            return self.create_order(
                battle.active_pokemon.available_z_moves[action - 4], z_move=True
            )
        elif (
            battle.can_mega_evolve
            and 0 <= action - 8 < len(battle.available_moves)
            and not battle.force_switch
        ):
            return self.create_order(battle.available_moves[action - 8], mega=True)
        elif (
            battle.can_dynamax
            and 0 <= action - 12 < len(battle.available_moves)
            and not battle.force_switch
        ):
            return self.create_order(battle.available_moves[action - 12], dynamax=True)
        elif 0 <= action - 16 < len(battle.available_switches):
            return self.create_order(battle.available_switches[action - 16])
        else:
            return self.choose_random_move(battle)

    def _init_battle(self, battle: Battle) -> None:
        self._observations[battle] = Queue()
        self._actions[battle] = Queue()

    def _complete_current_battle(self) -> None:
        """Completes the current battle by performing random moves."""
        done = self._current_battle.finished
        while not done:
            _, _, done, _ = self.step(np.random.choice(self._ACTION_SPACE))

    def _compute_reward(self, battle: Battle) -> float:
        return self._reward_computing_helper(
            battle,
            fainted_value = config.get_fainted_reward(),
            hp_value = config.get_hp_reward(),
            starting_value = config.get_starting_value(),
            status_value = config.get_status_value(),
            victory_value = config.get_victory_value()
        )

    def _embed_battle(self, battle: Battle) -> Any:
        # Rescale to 100 to facilitate learning
        battle_turn = battle.turn / 100

        # Check side conditions -- Reflect, Stealth Rock, etc.
        our_side_conditions = self._side_condition_id(battle.side_conditions)
        opponent_side_conditions = self._side_condition_id(battle.opponent_side_conditions)

        # Check weather and pseudoweather
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

        # Dynamax status
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
        
        # Mega/Z-Move status
        if battle.can_mega_evolve:
            our_mega_evolve_status = 1.0
        else:
            our_mega_evolve_status = 0.0
        
        if battle.can_z_move:
            our_z_move_status = 1.0
        else:
            our_z_move_status = 0.0

        # Effects -- Leech Seed, Substitute, etc.
        # Obviously only need to check active Pokemon
        our_effects = np.zeros(len(Effect))
        opponent_effects = np.zeros(len(Effect))

        effect_index = 0
        for effect in Effect:
            if effect in battle.active_pokemon.effects:
                our_effects[effect_index] = 1
            if effect in battle.opponent_active_pokemon.effects:
                opponent_effects[effect_index] = 1
            effect_index += 1

        # Team status
        remaining_mon_team = (
            len([mon for mon in battle.team.values() if mon.fainted]) / 6
        )
        remaining_mon_opponent = (
            len([mon for mon in battle.opponent_team.values() if mon.fainted]) / 6
        )

        active_move_observations = self._gather_move_observations(battle.available_moves[:NUM_MOVES], battle.opponent_active_pokemon)

        our_pokemon_observations = []
        for mon in battle.team.values():
            pokemon_observations = self._gather_pokemon_observations(mon, battle.opponent_active_pokemon)
            if len(pokemon_observations) != 78:
                raise Exception()
            our_pokemon_observations = np.append(our_pokemon_observations, pokemon_observations)

        opponent_pokemon_observations = []
        for mon in battle.opponent_team.values():
            pokemon_observations = self._gather_pokemon_observations(mon, battle.active_pokemon)
            if len(pokemon_observations) != 78:
                raise Exception()
            opponent_pokemon_observations = np.append(opponent_pokemon_observations, pokemon_observations)
        remaining_backfill = 6 - len(battle.opponent_team)
        opponent_pokemon_observations = np.append(opponent_pokemon_observations, np.negative(np.ones(78 * remaining_backfill)))

        if len(our_pokemon_observations) != len(opponent_pokemon_observations):
            raise Exception()
    
        final_vector = np.concatenate(
            [
                [battle_turn],
                self._taken_actions,
                [our_side_conditions, opponent_side_conditions],
                [weather, field_id],
                [our_dynamax_turns_left, opponent_dynamax_turns_left, our_dynamax_status, opponent_dynamax_status],
                [our_mega_evolve_status, our_z_move_status],
                our_effects,
                opponent_effects,
                [remaining_mon_team, remaining_mon_opponent],
                active_move_observations,
                our_pokemon_observations,
                opponent_pokemon_observations
            ]
        )

        if len(final_vector) != self._get_layer_size():
            raise Exception()

        return final_vector

    def _gather_pokemon_observations(self, pkm : Pokemon, opponent_pkm: Pokemon):
        base_stat_total = np.ones(len(AVAILABLE_STATS) - 1)

        for i in range(len(AVAILABLE_STATS)):
            stat = AVAILABLE_STATS[i]

            # Ditch accuracy
            if stat == "accuracy":
                continue

            # Correct evasion to HP
            if stat == "evasion":
                stat = "hp"

            base_stat_total[i] = pkm.base_stats[stat] / 255

        type_1 = int(pkm.type_1) / len(PokemonType)
        if pkm.type_2 is None:
            type_2 = -1.0
        else:
            type_2 = int(pkm.type_2) / len(PokemonType)

        if pkm.status is None:
            status = -1
        else:
            status = int(pkm.status) / len(Status)

        if pkm.ability is not None:
            ability = ABILITYDEX[to_id_str(pkm.ability)] / len(ABILITYDEX)
        else:
            ability = -1

        try:
            item = ITEMS[to_id_str(pkm.item)]["num"] / len(ITEMS)
        except (AttributeError, KeyError, TypeError):
            item = -1

        moves = self._gather_move_observations(list(pkm.moves.values())[:NUM_MOVES], opponent_pkm)

        boosts = np.zeros(len(AVAILABLE_STATS))
        for i in range(len(AVAILABLE_STATS)):
            stat = AVAILABLE_STATS[i]
            try:
                boosts[i] = pkm.boosts[stat] / 6
            except KeyError:
                pass

        pkm_vector = np.concatenate(
            [
                base_stat_total,
                [type_1, type_2],
                [status],
                [ability],
                [item],
                moves,
                boosts
            ]
        )

        return pkm_vector

    def _gather_move_observations(self, moves : List[Move], opponent_pkm : Pokemon):
         # Moves for the active Pokemon
        # -1 indicates that the move does not have a base power
        # or is not available
        moves_base_power = -np.ones(NUM_MOVES)
        moves_dmg_multiplier = np.ones(NUM_MOVES)
        moves_categories = -np.ones(NUM_MOVES)
        moves_switch = -np.ones(NUM_MOVES)
        moves_heal = -np.ones(NUM_MOVES)
        moves_recoil = -np.ones(NUM_MOVES)
        moves_sleep_usable = -np.ones(NUM_MOVES)
        moves_stall = -np.ones(NUM_MOVES)

        moves_all_boosts = np.zeros(NUM_MOVES * len(AVAILABLE_STATS))

        missing_moves = NUM_MOVES - len(moves)
        for i in range(missing_moves):
            moves += [EmptyMove("unknown")]

        if len(moves) != NUM_MOVES:
            raise Exception()
        
        for i, move in enumerate(moves):
            if move.is_empty:
                continue

            moves_base_power[i] = (
                move.base_power / 100
            )  # Simple rescaling to facilitate learning

            moves_categories[i] = int(move.category) / len(MoveCategory)

            if move.force_switch:
                moves_switch[i] = 1
            else:
                moves_switch[i] = 0

            if move.sleep_usable:
                moves_sleep_usable[i] = 1
            else:
                moves_sleep_usable[i] = 0

            if move.stalling_move:
                moves_stall[i] = 1
            else:
                moves_stall[i] = 0

            moves_heal[i] = move.heal
            moves_recoil[i] = move.recoil

            if move.type:
                moves_dmg_multiplier[i] = move.type.damage_multiplier(
                    opponent_pkm.type_1,
                    opponent_pkm.type_2,
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

        
        moves_vector = np.concatenate(
            [
                moves_base_power,
                moves_dmg_multiplier,
                moves_categories,
                moves_switch,
                moves_heal,
                moves_recoil,
                moves_sleep_usable,
                moves_stall,
                moves_all_boosts
            ]
        )

        return moves_vector

    def _side_condition_id(self, side_conditions : Set[SideCondition]) -> float:
        output = 0.0

        for condition in side_conditions:
            condition_bit = 1 << int(condition)
            output += condition_bit

        return output / (1 << len(SideCondition))

    def _reward_computing_helper(
        self,
        battle: Battle,
        *,
        fainted_value: float = 0.0,
        hp_value: float = 0.0,
        number_of_pokemons: int = 6,
        starting_value: float = 0.0,
        status_value: float = 0.0,
        victory_value: float = 1.0,
    ) -> float:
        """A helper function to compute rewards.

        The reward is computed by computing the value of a game state, and by comparing
        it to the last state.

        State values are computed by weighting different factor. Fainted pokemons,
        their remaining HP, inflicted statuses and winning are taken into account.

        For instance, if the last time this function was called for battle A it had
        a state value of 8 and this call leads to a value of 9, the returned reward will
        be 9 - 8 = 1.

        Consider a single battle where each player has 6 pokemons. No opponent pokemon
        has fainted, but our team has one fainted pokemon. Three opposing pokemons are
        burned. We have one pokemon missing half of its HP, and our fainted pokemon has
        no HP left.

        The value of this state will be:

        - With fainted value: 1, status value: 0.5, hp value: 1:
            = - 1 (fainted) + 3 * 0.5 (status) - 1.5 (our hp) = -1
        - With fainted value: 3, status value: 0, hp value: 1:
            = - 3 + 3 * 0 - 1.5 = -4.5

        :param battle: The battle for which to compute rewards.
        :type battle: Battle
        :param fainted_value: The reward weight for fainted pokemons. Defaults to 0.
        :type fainted_value: float
        :param hp_value: The reward weight for hp per pokemon. Defaults to 0.
        :type hp_value: float
        :param number_of_pokemons: The number of pokemons per team. Defaults to 6.
        :type number_of_pokemons: int
        :param starting_value: The default reference value evaluation. Defaults to 0.
        :type starting_value: float
        :param status_value: The reward value per non-fainted status. Defaults to 0.
        :type status_value: float
        :param victory_value: The reward value for winning. Defaults to 1.
        :type victory_value: float
        :return: The reward.
        :rtype: float
        """
        if battle not in self._reward_buffer:
            self._reward_buffer[battle] = starting_value
        current_value = 0

        for mon in battle.team.values():
            current_value += mon.current_hp_fraction * hp_value
            if mon.fainted:
                current_value -= fainted_value
            elif mon.status is not None:
                current_value -= status_value

        current_value += (number_of_pokemons - len(battle.team)) * hp_value

        for mon in battle.opponent_team.values():
            current_value -= mon.current_hp_fraction * hp_value
            if mon.fainted:
                current_value += fainted_value
            elif mon.status is not None:
                current_value += status_value

        current_value -= (number_of_pokemons - len(battle.opponent_team)) * hp_value

        if battle.won:
            current_value += victory_value
        elif battle.lost:
            current_value -= victory_value

        to_return = current_value - self._reward_buffer[battle]
        self._reward_buffer[battle] = current_value

        return to_return

    def _get_layer_size(self) -> int:
        return 1377

    # This is the function that will be used to train the dqn
    def _dqn_training(self, player, dqn, nb_steps):
        cp_callback = tf.keras.callbacks.ModelCheckpoint(filepath=self._get_checkpoint_file(),
                                                        save_weights_only=True,
                                                        verbose=0)
        dqn.fit(player, nb_steps=nb_steps, callbacks=[self, cp_callback])
        print("Fit complete; finishing up battle")

    def _train(self) -> None:
        if config.get_train_against_ladder():
            opponent_string = "ladder"
            opponent = None
        else:
            if self.validate:
                # Run tests of untrained model
                print("Evaluating untrained model")
                self._evaluate_dqn()

            opponent = MaxDamagePlayer(battle_format=self.format)
            opponent_string = opponent.username

        if self.use_checkpoint:
            print("Trying to load from checkpoint")
            checkpoint_dir = config.get_checkpoint_dir()
            try:
                latest = tf.train.latest_checkpoint(checkpoint_dir)
                self.model.load_weights(latest)
            
                if self.validate:
                    # Run tests of loaded model
                    print("Evaluating loaded model")
                    self._evaluate_dqn()
            except (AttributeError, ValueError):
                print("Unable to load checkpoint")

        nb_steps = config.get_num_training_steps()

        print("Beginning training with " + str(nb_steps) + " steps against " + opponent_string)
        
        # Training
        train_start_time = time.time()
        try:
            self.play_against(
                env_algorithm=self._dqn_training,
                opponent=opponent,
                env_algorithm_kwargs={"dqn": self.dqn, "nb_steps": nb_steps},
            )
        except KeyboardInterrupt:
            print("\nKeyboard interrupt; going to finish up current battle and abort")
            self.complete_current_battle()
            print("Final battle complete")

        train_end_time = train_start_time - time.time()

        print("Training complete in " + str(train_end_time) + " seconds. win rate: " + str(self.win_rate * 100.0) + "%")

        if self.validate:
            self._evaluate_dqn()

    def _dqn_evaluation(self, player, dqn, nb_episodes):
        # Reset battle statistics
        player.reset_battles()
        dqn.test(player, nb_episodes=nb_episodes, visualize=True, verbose=True)

        print(
            "DQN Evaluation: %d victories out of %d episodes"
            % (player.n_won_battles, nb_episodes)
        )

    def _evaluate_dqn(self) -> None:
        opponent = DefaultPlayer(battle_format="gen8randombattle")
        second_opponent = RandomPlayer(battle_format="gen8randombattle")
        third_opponent = MaxDamagePlayer(battle_format="gen8randombattle")
        
        # Evaluation
        evaluate_start_time = time.time()
        print("Results against default player:")
        self.play_against(
            env_algorithm=self._dqn_evaluation,
            opponent=opponent,
            env_algorithm_kwargs={"dqn": self.dqn, "nb_episodes": config.get_num_evaluation_episodes()},
        )
        evaluate_end_time = time.time() - evaluate_start_time
        print("Evaluation took " + str(evaluate_end_time) + " seconds")

        evaluate_start_time = time.time()
        print("Results against random player:")
        self.play_against(
            env_algorithm=self._dqn_evaluation,
            opponent=second_opponent,
            env_algorithm_kwargs={"dqn": self.dqn, "nb_episodes": config.get_num_evaluation_episodes()},
        )
        evaluate_end_time = time.time() - evaluate_start_time
        print("Evaluation took " + str(evaluate_end_time) + " seconds")

        evaluate_start_time = time.time()
        print("\nResults against max player:")
        self.play_against(
            env_algorithm=self._dqn_evaluation,
            opponent=third_opponent,
            env_algorithm_kwargs={"dqn": self.dqn, "nb_episodes": config.get_num_evaluation_episodes()},
        )
        evaluate_end_time = time.time() - evaluate_start_time
        print("Evaluation took " + str(evaluate_end_time) + " seconds")

    def _step_timeout(self):
        execution_time = time.time() - self._last_step_start_time
        print("\nStep timed out after " + str(execution_time) + " seconds!\n")
        # Raises KeyboardInterrupt
        _thread.interrupt_main()

    def _get_checkpoint_file(self) -> str:
        checkpoint_dir = config.get_checkpoint_dir()
        return os.path.join(checkpoint_dir, self.format + ".ckpt")
