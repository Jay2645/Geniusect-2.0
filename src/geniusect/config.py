#!/usr/bin/env python3

import configparser
import errno
import sys
import logging
import os

import src.geniusect.update_data as updater

from tensorflow.keras.layers import Dense, Flatten, Dropout
from tensorflow.keras.models import Sequential, Model

log_level=logging.INFO

# Update our stored data with the most recent from the server
updater.update_pokedex()
updater.update_itemdex()
updater.update_movedex()
updater.update_learnset()

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
    return int(ai_config.get("Train", "NumEvaluationEpisodes"))

def get_train_against_ladder() -> bool:
    return ai_config.getboolean("Train", "TrainAgainstLadder")

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

def build_model(input_layer_size, output_layer_size) -> Model:
    
    model = Sequential()
    model.add(Dense(2048, activation="elu", input_shape=(1, input_layer_size)))
    model.add(Flatten())
    model.add(Dropout(get_input_drop_percent()))
    model.add(Dense(1024, activation="elu"))
    model.add(Dropout(get_hidden_drop_percent()))
    model.add(Dense(256, activation="elu"))
    model.add(Dropout(get_hidden_drop_percent()))
    model.add(Dense(64, activation="elu"))
    model.add(Dropout(get_hidden_drop_percent()))
    model.add(Dense(output_layer_size, activation="linear"))

    model.summary()

    return model