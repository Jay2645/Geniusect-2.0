#!/usr/bin/env python3

# Update our stored data with the most recent from the server
from numpy.lib.polynomial import RankWarning
import src.geniusect.update_data as updater
updater.update_pokedex()
updater.update_itemdex()
updater.update_movedex()
updater.update_learnset()

import codecs
import configparser
import errno
import json
import logging
import os
import sys
import time
import shutil

import matplotlib.pyplot as plt
import numpy as np

from tensorflow.keras.layers import Dense, Flatten, Dropout, LeakyReLU, LSTM, Activation
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.optimizers import Adam

from src.geniusect.neural_net.dqn_agent import DQNAgent
from rl.policy import LinearAnnealedPolicy, EpsGreedyQPolicy
from rl.memory import SequentialMemory

from poke_env.player_configuration import PlayerConfiguration
from poke_env.player.player import Player
from poke_env.player.random_player import RandomPlayer


log_level=logging.INFO

# Import the config
secret_config = configparser.ConfigParser()
secret_config.read(["secrets.cfg"])

ai_config = configparser.ConfigParser()
ai_config.read(["ai_variables.cfg"])

MEMORY_WINDOW = 5

def get_starting_tryhard() -> float:
    return float(ai_config.get("Opponent", "StartingTryhard"))

def get_tryhard_floor() -> float:
    return float(ai_config.get("Opponent", "TryhardFloor"))

def get_bot_username() -> str:
    return secret_config.get("Bot", "Username")

def get_bot_password() -> str:
    return secret_config.get("Bot", "Password")

def get_human_username() -> str:
    return secret_config.get("Human", "Username")

def get_fainted_reward() -> float:
    return float(ai_config.get("Rewards", "FaintedReward"))

def get_hp_reward() -> float:
    return float(ai_config.get("Rewards", "HPReward"))

def get_starting_value() -> float:
    return float(ai_config.get("Rewards", "ReferenceValue"))

def get_status_value() -> float:
    return float(ai_config.get("Rewards", "StatusReward"))

def get_victory_value() -> float:
    return float(ai_config.get("Rewards", "VictoryReward"))

def get_num_training_steps() -> int:
    return int(ai_config.get("Train", "NumTrainingSteps"))
    
def get_num_training_steps() -> int:
    return int(ai_config.get("Train", "NumTrainingSteps"))
    
def get_num_evaluation_episodes() -> int:
    return int(ai_config.get("Train", "NumEvaluationEpisodes")) - 1

def get_train_against_ladder() -> bool:
    return ai_config.get("Opponent", "Opponent").lower() == "ladder"

from src.geniusect.neural_net.dqn_history import DQNHistory
from src.geniusect.player.max_damage_player import MaxDamagePlayer
from src.geniusect.player.default_player import DefaultPlayer
from poke_env.player.baselines import SimpleHeuristicsPlayer

if get_train_against_ladder():
    opponents = {}
else:
    opponents = {
        "default": DefaultPlayer(battle_format="gen8randombattle"), 
        "random": RandomPlayer(battle_format="gen8randombattle"), 
        "max": MaxDamagePlayer(battle_format="gen8randombattle"),
        "heuristics": SimpleHeuristicsPlayer(battle_format="gen8randombattle")
    }

def get_opponent(battle_format = "gen8randombattle", cycle_count = 0) -> Player:
    opponent_string = ai_config.get("Opponent", "Opponent").lower()
    opponent_num = cycle_count % len(opponents)

    if opponent_string == "ladder":
        return None
    elif opponent_string == "random" or (opponent_string == "cycle" and opponent_num == 0):
        return opponents["random"]
    elif opponent_string == "default" or (opponent_string == "cycle" and opponent_num == 1):
        return opponents["default"]
    elif opponent_string == "max" or (opponent_string == "cycle" and opponent_num == 2):
        return opponents["max"]
    elif opponent_string == "heuristics" or (opponent_string == "cycle" and opponent_num == 3):
        return opponents["heuristics"]
    elif opponent_string == "self":
        from src.geniusect.player.reinforcement_learning_player import RLPlayer
        return RLPlayer(train=False, validate=False, load_from_checkpoint=True, battle_format=battle_format, player_configuration=PlayerConfiguration("RL Player " + str(cycle_count), ""))
    else:
        raise AttributeError()

def get_input_drop_percent() -> float:
    return 1.0 - float(ai_config.get("Train", "DropoutKeepInputLayer"))

def get_hidden_drop_percent() -> float:
    return 1.0 - float(ai_config.get("Train", "DropoutKeepHiddenLayer"))

def get_learning_rate() -> float:
    return float(ai_config.get("Train", "LearningRate"))

def get_epsilon() -> float:
    return float(ai_config.get("Train", "Epsilon"))

def get_load_from_checkpoint() -> bool:
    return ai_config.getboolean("Saving", "AutoLoadFromCheckpoint")

def get_use_checkpoint() -> bool:
    return ai_config.getboolean("Saving", "UseCheckpoint")

def get_checkpoint_dir(format = "") -> str:
    checkpoint_dir = ai_config.get("Saving", "CheckpointDir")
    complete_path = os.path.join("data", checkpoint_dir)

    if format != "":
        complete_path = os.path.join(complete_path, format)

    complete_path = os.path.join(complete_path, "logs")

    try:
        os.makedirs(complete_path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return complete_path

def get_tensorboard_log_dir(format = "") -> str:
    return get_checkpoint_dir(format)

def get_step_timeout() -> float:
    return float(ai_config.get("Execution", "StepTimeout"))

def get_num_warmup_steps() -> int:
    return int(ai_config.get("DQN", "NumberWarmupSteps"))
    
def get_gamma() -> float:
    return float(ai_config.get("DQN", "Gamma"))

def get_target_model_update() -> int:
    return int(ai_config.get("DQN", "TargetModelUpdate"))

def get_delta_clip() -> float:
    return float(ai_config.get("DQN", "DeltaClip"))

def get_use_double_dqn() -> bool:
    return ai_config.getboolean("DQN", "UseDoubleDQN")

def build_dqn(model : Model, output_layer_size : int):
    memory = SequentialMemory(limit=20000, window_length=MEMORY_WINDOW)

    # Simple epsilon greedy
    policy = LinearAnnealedPolicy(
        EpsGreedyQPolicy(),
        attr="eps",
        value_max=1.0,
        value_min=0.0,
        value_test=0,
        nb_steps=(get_num_warmup_steps() * 50),
    )

    # Defining our DQN
    dqn = DQNAgent(
        model=model,
        nb_actions=output_layer_size,
        policy=policy,
        memory=memory,
        nb_steps_warmup=get_num_warmup_steps(),
        gamma=get_gamma(),
        target_model_update=get_target_model_update(),
        delta_clip=get_delta_clip(),
        enable_double_dqn=get_use_double_dqn(),
    )

    print("Learning rate " + str(get_learning_rate()) + " and epsilon " + str(get_epsilon()))

    optimizer = Adam(lr=get_learning_rate(), epsilon=get_epsilon())

    dqn.compile(optimizer, metrics=["mae"])
    return dqn

def build_model(input_layer_size, nb_actions) -> Model:
    model = Sequential()

# #    model.add(Dense(input_layer_size, name="Input", input_shape=(MEMORY_WINDOW, input_layer_size)))
# #    model.add(LeakyReLU(alpha=0.1))
# #    model.add(Flatten())
# #    model.add(Dropout(get_input_drop_percent(), name="Input_Drop"))
# #    model.add(Dense(1024, name="Hidden_Layer_1"))
# #    model.add(LeakyReLU(alpha=0.1))
# #    model.add(Dropout(get_hidden_drop_percent(), name = "Hidden_Drop_1"))
# #    model.add(Dense(512, name="Hidden_Layer_2"))
# #    model.add(LeakyReLU(alpha=0.1))
# #    model.add(Dropout(get_hidden_drop_percent(), name = "Hidden_Drop_2"))
# #    model.add(Dense(256, name="Hidden_Layer_3"))
# #    model.add(LeakyReLU(alpha=0.1))
# #   model.add(Dropout(get_hidden_drop_percent(), name = "Hidden_Drop_3"))
#     model.add(LSTM(1024, name="Input_LSTM", dropout=get_input_drop_percent(), return_sequences=True, input_shape=(MEMORY_WINDOW, input_layer_size)))
#     model.add(Dense(512, name="Hidden_Layer_1"))
#     model.add(LeakyReLU(alpha=0.1))
#     model.add(Dropout(get_hidden_drop_percent(), name = "Hidden_Drop_1"))
#     model.add(LSTM(256, name="Hidden_LSTM_1", dropout=get_hidden_drop_percent(), return_sequences=True))
#     model.add(Dense(128, name="Hidden_Layer_2"))
#     model.add(LeakyReLU(alpha=0.1))
#     model.add(Dropout(get_hidden_drop_percent(), name = "Hidden_Drop_2"))
#     model.add(LSTM(64, name="Hidden_LSTM_2", dropout=get_hidden_drop_percent()))
#     model.add(Dense(nb_actions, name="Inner_Output", activation="softmax"))
#     model.add(Dense(nb_actions, name="Model_Output", activation="linear"))

    model.add(Flatten(input_shape=(MEMORY_WINDOW, input_layer_size)))
    model.add(Dropout(0.2, name = "Input_Drop"))
    model.add(Dense(units=64*4))
    model.add(Activation('tanh'))
    model.add(Dropout(0.5, name = "Hidden_Drop_1"))
    model.add(Dense(units=64*4))
    model.add(Activation('tanh'))
    model.add(Dropout(0.5, name = "Hidden_Drop_2"))
    model.add(Dense(nb_actions))
    model.add(Activation('linear'))
    model.summary()

    return model

def plot_history(history : DQNHistory, model_name : str, opponent_name : str, batch_num : int):
    history_path = os.path.join("data", "models", model_name)

    try:
        os.makedirs(history_path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    plt.clf()

    try:
        # Plot history: Episode Rewards
        rewards = history.history['episode_rewards']
        session_num_episodes = len(rewards)
        plot_title = " for Geniusect over " + str(history.current_step) + " steps (" + str(session_num_episodes) + " games)"

        reward_idx = [i + 1 for i in range(session_num_episodes)]
        plt.scatter(reward_idx, rewards)

        fitted_trendline = np.polyfit(reward_idx, rewards, 1)
        fitted_trendline_1d = np.poly1d(fitted_trendline)
        plt.plot(reward_idx, fitted_trendline_1d(reward_idx), "r--")
        plt.plot(reward_idx, [0 for i in range(session_num_episodes)], "k:")

        plt.title("Game Rewards" + plot_title)
        plt.ylabel("Reward")
        plt.xlabel("Game")

        plot_path = os.path.join(history_path, "episode-reward.png")
        plt.savefig(plot_path)
        plt.clf()

        handles = []

        # The DQNAgent uses Huber Loss to calculate loss
        # The Huber loss function balances between MAE and MSE
        plt.title("Huber Loss" + plot_title)
        plt.ylabel('Loss')
        plt.xlabel('Game')
        handles = plt.plot(history.history['loss'], label='Loss')
        plt.legend(handles=handles)
        plot_path = os.path.join(history_path, "loss.png")
        plt.savefig(plot_path)
        plt.clf()

        plt.title("Mean Absolute Error" + plot_title)
        plt.ylabel('Mean Absolute Error')
        plt.xlabel('Game')
        handles = plt.plot(history.history['mae'], label='Mean Absolute Error')
        plt.legend(handles=handles)
        plot_path = os.path.join(history_path, "mae.png")
        plt.savefig(plot_path)
        plt.clf()

        plt.title("Mean Q" + plot_title)
        plt.ylabel('Mean Q')
        plt.xlabel('Game')
        handles = plt.plot(history.history['mean_q'], label='Mean Q')
        plt.legend(handles=handles)
        plot_path = os.path.join(history_path, "mean_q.png")
        plt.savefig(plot_path)
        plt.clf()

        plt.title("Best Q" + plot_title)
        plt.ylabel('Best Q')
        plt.xlabel('Step')
        handles = plt.plot(history.history['best_q'], label='Best Q')
        plt.legend(handles=handles)
        plot_path = os.path.join(history_path, "best_q.png")
        plt.savefig(plot_path)
        plt.clf()

        plt.title("Current Exploration Chance" + plot_title)
        plt.ylabel('Epsilon')
        plt.xlabel('Game')
        handles = plt.plot(history.history['mean_eps'], label='Epsilon')
        plt.legend(handles=handles)
        plot_path = os.path.join(history_path, "mean_eps.png")
        plt.savefig(plot_path)
        plt.clf()

        plt.title("Win Rate" + plot_title)
        plt.ylabel('Win Rate')
        plt.xlabel('Game')
        handles = plt.plot(history.history['win_rate'], label='Win Rate')
        plt.legend(handles=handles)
        plot_path = os.path.join(history_path, "win_rate.png")
        plt.savefig(plot_path)
        plt.clf()
    except (RankWarning, KeyError, ValueError, PermissionError):
        pass
