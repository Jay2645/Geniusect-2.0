#!/usr/bin/env python3

import math
import os
import threading
import _thread
import time

import numpy as np
import tensorflow as tf

import src.geniusect.config as config

from rl.callbacks import Callback

from typing import Any, Callable, List, Optional, Tuple, Union, Set

from poke_env.data import ABILITYDEX, ITEMS, to_id_str
from poke_env.environment.battle import Battle
from poke_env.environment.effect import Effect
from poke_env.environment.field import Field
from poke_env.environment.move import Move, EmptyMove
from poke_env.environment.move_category import MoveCategory
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

from src.geniusect.neural_net.dqn_history import DQNHistory
from src.geniusect.player.max_damage_player import MaxDamagePlayer
from src.geniusect.player.default_player import DefaultPlayer

AVAILABLE_STATS = ["atk", "def", "spa", "spd", "spe", "evasion", "accuracy"]
NUM_MOVES = 4
MOVE_MEMORY = 100

CEND    = '\33[0m'
CBLUE   = '\33[34m'
CGREEN  = '\33[32m'
CYELLOW = '\33[33m'

tf.random.set_seed(0)
np.random.seed(0)
os.system('color')

class RLPlayer(Gen8EnvSinglePlayer, Callback):
    def __init__(
        self,
        train = True,
        validate = True,
        load_from_checkpoint = False,
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

        input_layer_size = self._get_layer_size()
        output_layer_size = len(self.action_space)
        self.model = config.build_model(input_layer_size, output_layer_size)
        self.dqn = config.build_dqn(self.model, output_layer_size)

        self.train = train
        self.use_checkpoint = load_from_checkpoint
        self.validate = validate
        self._validate_untrained = False

        self._history = DQNHistory()
        self._timer = None
        self._last_step_start_time = time.time()
        # Only join lobbies on localhost
        self.done_joining_lobby = self.validate and "localhost" not in self._server_url

        self._taken_actions = np.negative(np.ones(MOVE_MEMORY))
        self._current_opponent = ""

        if self.train:
            self._train()

    async def _battle_started_callback(self, battle : Battle) -> None:
        if not self.done_joining_lobby:
            await self._send_message("/join lobby")
            self.done_joining_lobby = True

        await self._send_message("/timer on", battle.battle_tag)
        await self._send_message("Hi, I'm a \"Deep Q\" learning bot named Geniusect! Every turn, I gather up to " + str(self._get_layer_size()) + " pieces of data from the game and feed them into a neural network.", battle.battle_tag)
        await self._send_message("If I do good (like making your Pokemon faint and keeping all of mine alive), I get a virtual lollipop. If I do bad, I get put into time-out. Eventually, I'll learn the rules of the game and what moves to make in the right situations so I get as many lollipops as I can.", battle.battle_tag)
        if self.n_finished_battles == 0:
            if self.train:
                await self._send_message("I'm in training and this is my first game this session. I'm basically going to do random things and learn how they change the game, so I can find out what's good and what's bad.", battle.battle_tag)
        else:
            if self.win_rate <= 0.6:
                is_dumb = "Despite my name, I'm actually pretty dumb. "
            else:
                is_dumb = ""
            await self._send_message(is_dumb + "I currently have a " + str(round(self.win_rate * 100.0)) + "% win rate out of " + str(self.n_finished_battles) + " games.", battle.battle_tag)
        await self._send_message("I won't be able to reply to you, since I'm a bot with no human directly supervising me (although you might see " + config.get_human_username() +  " spectate from time to time).", battle.battle_tag)

    async def _battle_finished_callback(self, battle : Battle) -> None:
        await super(RLPlayer, self)._battle_finished_callback(battle)

        # Forget all moves we've done as they are no longer relevant
        self._taken_actions = np.negative(np.ones(MOVE_MEMORY))

        if self.validate and self.done_joining_lobby:
            await self._send_message("  Turn %4d. | [%s][%3d/%3dhp] %10.10s - %10.10s [%3d%%hp][%s]"
            % (
                battle.turn,
                "".join(
                    [
                        "⦻" if mon.fainted else "●"
                        for mon in battle.team.values()
                    ]
                ),
                battle.active_pokemon.current_hp or 0,
                battle.active_pokemon.max_hp or 0,
                battle.active_pokemon.species,
                battle.opponent_active_pokemon.species,  # pyre-ignore
                battle.opponent_active_pokemon.current_hp  # pyre-ignore
                or 0,
                "".join(
                    [
                        "⦻" if mon.fainted else "●"
                        for mon in battle.opponent_team.values()
                    ]
                ),
            ),
            "lobby")

    def _action_to_move(self, action: int, battle: Battle) -> str:
        # Place oldest action at the front of the list (rotating/shifting the list by 1)
        # e.g. 4,3,2,1 -> 1,4,3,2
        self._taken_actions = np.roll(self._taken_actions, 1)

        # Place most recent taken action at index 0
        # e.g. 5,4,3,2
        self._taken_actions[0] = action / len(self._ACTION_SPACE)

        return super(RLPlayer, self)._action_to_move(action, battle)

    def embed_battle(self, battle):
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

    def compute_reward(self, battle) -> float:
        return self.reward_computing_helper(
            battle,
            fainted_value = config.get_fainted_reward(),
            hp_value = config.get_hp_reward(),
            starting_value = config.get_starting_value(),
            status_value = config.get_status_value(),
            victory_value = config.get_victory_value()
        )

    def on_step_begin(self, step, logs):
        self._last_step_start_time = time.time()

        timeout = config.get_step_timeout()

        self._timer = threading.Timer(timeout, self._step_timeout)
        self._timer.start()

    def _step_timeout(self):
        execution_time = time.time() - self._last_step_start_time
        print("\nStep timed out after " + str(execution_time) + " seconds!\n")
        # Raises KeyboardInterrupt
        _thread.interrupt_main()

    def on_step_end(self, step, logs):
        self._timer.cancel()
        self._timer = None

    def on_episode_end(self, episode, logs):
        """ Render environment at the end of each action """
        if not self.done_joining_lobby:
            print("")
            self.render(mode='human')

    def _get_checkpoint_file(self) -> str:
        checkpoint_dir = config.get_checkpoint_dir()
        return os.path.join(checkpoint_dir, self.format + ".ckpt")

    def _get_layer_size(self) -> int:
        return 1381

    # This is the function that will be used to train the dqn
    def _dqn_training(self, player, dqn, nb_steps):
        cp_callback = tf.keras.callbacks.ModelCheckpoint(filepath=self._get_checkpoint_file(),
                                                            save_weights_only=True,
                                                    verbose=0)
        try:
            dqn.fit(player, nb_steps=nb_steps, callbacks=[self, cp_callback, self._history])
        except Exception:
            pass

    def _train(self) -> None:
        if config.get_train_against_ladder():
            self._current_opponent = "ladder"
            opponent = None
        else:
            if self.validate and self._validate_untrained:
                # Run tests of untrained model
                print("Evaluating untrained model" + CYELLOW)
                self._evaluate_dqn()
                print(CEND)

        cached_opponent = self._current_opponent

        if self.use_checkpoint:
            print("Trying to load from checkpoint")
            checkpoint_dir = config.get_checkpoint_dir()
            try:
                latest = tf.train.latest_checkpoint(checkpoint_dir)
                self.model.load_weights(latest)
            
                if self.validate:
                    # Run tests of loaded model
                    print("Evaluating loaded model" + CBLUE)
                    self._evaluate_dqn()
                    print(CEND)
            except (AttributeError, ValueError):
                print("Unable to load checkpoint")

        self._current_opponent = cached_opponent

        nb_steps = config.get_num_training_steps()

        print("Beginning training with " + str(nb_steps) + " steps")
        
        # Training
        train_start_time = time.time()
        try:
            NUM_INTERVAL_STEPS = 50000
            num_intervals = math.ceil(nb_steps / NUM_INTERVAL_STEPS)
            remaining_steps = nb_steps
            for i in range(num_intervals):
                step_count = min(remaining_steps, NUM_INTERVAL_STEPS)
                remaining_steps -= step_count

                if self._current_opponent != "ladder":
                    opponent = config.get_opponent(battle_format=self.format, cycle_count=i)
                    self._current_opponent = opponent.username

                print("Playing against " + self._current_opponent)

                self.play_against(
                    env_algorithm=self._dqn_training,
                    opponent=opponent,
                    env_algorithm_kwargs={"dqn": self.dqn, "nb_steps": step_count},
                )
                
                config.plot_history(self._history, self.format, self._current_opponent, i)

        except KeyboardInterrupt:
            print("\nKeyboard interrupt; going to finish up current battle and abort")
            self.complete_current_battle()
            print("Final battle complete")

        train_end_time = train_start_time - time.time()

        print("Training complete in " + str(train_end_time) + " seconds. win rate: " + str(self.win_rate * 100.0) + "%")
        self._current_opponent = ""

        if self.validate:
            print(CGREEN)
            self._evaluate_dqn()
            print(CEND)

    def _dqn_evaluation(self, player, dqn, nb_episodes):
        # Reset battle statistics
        player.reset_battles()
        dqn.test(player, nb_episodes=nb_episodes, visualize=True, verbose=True)

    def _evaluate_dqn(self) -> None:
        nb_episodes = config.get_num_evaluation_episodes()

        opponents = [
            DefaultPlayer(battle_format="gen8randombattle"), 
            RandomPlayer(battle_format="gen8randombattle"), 
            MaxDamagePlayer(battle_format="gen8randombattle")
        ]

        wins = []

        # Evaluation
        for opponent in opponents:
            evaluate_start_time = time.time()
            self._current_opponent = opponent.username
            print("Results against " + self._current_opponent + ":")

            self.play_against(
                env_algorithm=self._dqn_evaluation,
                opponent=opponent,
                env_algorithm_kwargs={"dqn": self.dqn, "nb_episodes": nb_episodes},
            )

            wins.append((self._current_opponent, self.n_won_battles, self.n_lost_battles))

            evaluate_end_time = time.time() - evaluate_start_time

            print(
                "DQN Evaluation: %d victories out of %d episodes against %s; took %d seconds"
                % (self.n_won_battles, nb_episodes + 1, self._current_opponent, evaluate_end_time)
            )

            time.sleep(3)
        print(wins)
        print("\n")

        time.sleep(5)

        self._current_opponent = ""
        return wins

    def _side_condition_id(self, side_conditions : Set[SideCondition]) -> float:
        output = 0.0

        for condition in side_conditions:
            condition_bit = 1 << int(condition)
            output += condition_bit

        return output / (1 << len(SideCondition))
