#!/usr/bin/env python3

import configparser
import sys

import src.geniusect.update_data as updater

import logging

log_level=logging.INFO

# Update our stored data with the most recent from the server
updater.update_pokedex()
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