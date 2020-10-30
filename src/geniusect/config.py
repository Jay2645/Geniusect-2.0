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

def get_bot_username() -> str:
	return secret_config.get("Bot", "Username")

def get_bot_password() -> str:
	return secret_config.get("Bot", "Password")

def get_human_username() -> str:
	return secret_config.get("Human", "Username")