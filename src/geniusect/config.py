#!/usr/bin/env python3

# Update our stored data with the most recent from the server
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

import matplotlib.pyplot as plt
import numpy as np

from tensorflow.keras.layers import Dense, Flatten, Dropout
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.optimizers import Adam

from rl.agents.dqn import DQNAgent
from rl.policy import LinearAnnealedPolicy, EpsGreedyQPolicy
from rl.memory import SequentialMemory

from poke_env.player.player import Player
from poke_env.player.random_player import RandomPlayer

from src.geniusect.neural_net.dqn_history import DQNHistory
from src.geniusect.player.max_damage_player import MaxDamagePlayer
from src.geniusect.player.default_player import DefaultPlayer

log_level=logging.INFO
cycle_offset = round(time.time()) % 3

# Import the config
secret_config = configparser.ConfigParser()
secret_config.read(["secrets.cfg"])

ai_config = configparser.ConfigParser()
ai_config.read(["ai_variables.cfg"])

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
    return ai_config.get("Train", "Opponent").lower() == "ladder"

def get_opponent(battle_format = "gen8randombattle", cycle_count = 0) -> Player:
    opponent_string = ai_config.get("Train", "Opponent").lower()
    opponent_num = (cycle_count + cycle_offset) % 3

    if opponent_string == "ladder":
        return None
    elif opponent_string == "default" or (opponent_string == "cycle" and opponent_num == 0):
        return DefaultPlayer(battle_format=battle_format)
    elif opponent_string == "random" or (opponent_string == "cycle" and opponent_num == 1):
        return RandomPlayer(battle_format=battle_format)
    elif opponent_string == "max" or (opponent_string == "cycle" and opponent_num == 2):
        return MaxDamagePlayer(battle_format=battle_format)
    else:
        raise AttributeError()

def get_input_drop_percent() -> float:
    return 1.0 - float(ai_config.get("Train", "DropoutKeepInputLayer"))

def get_hidden_drop_percent() -> float:
    return 1.0 - float(ai_config.get("Train", "DropoutKeepHiddenLayer"))

def get_load_from_checkpoint() -> bool:
    return ai_config.getboolean("Saving", "AutoLoadFromCheckpoint")

def get_use_checkpoint() -> bool:
    return ai_config.getboolean("Saving", "UseCheckpoint")

def get_checkpoint_dir() -> str:
    checkpoint_dir = ai_config.get("Saving", "CheckpointDir")
    complete_path = os.path.join("data", checkpoint_dir)

    try:
        os.makedirs(complete_path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return complete_path

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
    memory = SequentialMemory(limit=get_num_training_steps(), window_length=1)

    # Simple epsilon greedy
    policy = LinearAnnealedPolicy(
        EpsGreedyQPolicy(),
        attr="eps",
        value_max=1.0,
        value_min=0.05,
        value_test=0,
        nb_steps=get_num_training_steps(),
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

    optimizer = Adam(lr=0.00025)

    dqn.compile(optimizer, metrics=["mae"])
    return dqn

def build_model(input_layer_size, output_layer_size) -> Model:
    model = Sequential()
    model.add(Dense(input_layer_size, activation="elu", input_shape=(1, input_layer_size)))
    model.add(Flatten())
    model.add(Dropout(get_input_drop_percent()))
    model.add(Dense(512, activation="elu"))
    model.add(Dropout(get_hidden_drop_percent()))
    model.add(Dense(output_layer_size, activation="linear"))
    model.add(Dropout(get_hidden_drop_percent()))
    model.add(Dense(output_layer_size, activation="linear"))

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

    # Plot history: Episode Rewards
    rewards = history.history['episode_rewards']
    reward_idx = [i + 1 for i in range(len(rewards))]
    plt.scatter(reward_idx, rewards)

    fitted_trendline = np.polyfit(reward_idx, rewards, 1)
    fitted_trendline_1d = np.poly1d(fitted_trendline)
    plt.plot(reward_idx, fitted_trendline_1d(reward_idx), "r--")

    plt.title("Game Rewards for Geniusect over " + str(len(rewards)) + " games")
    plt.ylabel("Reward")
    plt.xlabel("Game")

    plot_path = os.path.join(history_path, "episode-reward-" + str(batch_num) + ".png")
    plt.savefig(plot_path)

    plt.clf()

    try:
        handles = []

        # The DQNAgent uses Huber Loss to calculate loss
        # The Huber loss function balances between MAE and MSE
        plt.title("Huber Loss for Geniusect over " + str(len(rewards)) + " games")
        plt.ylabel('Loss')
        plt.xlabel('Game')
        handles = plt.plot(history.history['loss'], label='Loss')
        plt.legend(handles=handles)
        plot_path = os.path.join(history_path, "loss-" + str(batch_num) + ".png")
        plt.savefig(plot_path)
        plt.clf()

        plt.title("Mean Absolute Error for Geniusect over " + str(len(rewards)) + " games")
        plt.ylabel('Mean Absolute Error')
        plt.xlabel('Game')
        handles = plt.plot(history.history['mae'], label='Mean Absolute Error')
        plt.legend(handles=handles)
        plot_path = os.path.join(history_path, "mae-" + str(batch_num) + ".png")
        plt.savefig(plot_path)
        plt.clf()

        plt.title("Mean Q for Geniusect over " + str(len(rewards)) + " games")
        plt.ylabel('Mean Q')
        plt.xlabel('Game')
        handles = plt.plot(history.history['mean_q'], label='Mean Q')
        plt.legend(handles=handles)
        plot_path = os.path.join(history_path, "mean_q-" + str(batch_num) + ".png")
        plt.savefig(plot_path)
        plt.clf()

        plt.title("Mean Epsilon for Geniusect over " + str(len(rewards)) + " games")
        plt.ylabel('Epsilon')
        plt.xlabel('Game')
        handles = plt.plot(history.history['mean_eps'], label='Epsilon')
        plt.legend(handles=handles)
        plot_path = os.path.join(history_path, "mean_eps-" + str(batch_num) + ".png")
        plt.savefig(plot_path)
        plt.clf()
    except KeyError:
        pass
