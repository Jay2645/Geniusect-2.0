#!/usr/bin/env python3

import os
import logging

def update_pokedex():
	print("Updating Pokedex")
	import src.updaters.pokedex_update_script
	
	POKEDEX_DATA_LOCATION = "poke_env/data/pokedex.json"
	os.remove(POKEDEX_DATA_LOCATION)
	os.rename("out.json", POKEDEX_DATA_LOCATION)

	print("Pokedex updated")

def update_movedex():
	print("Updating Movedex")
	import src.updaters.move_update_script
	
	POKEDEX_DATA_LOCATION = "poke_env/data/moves.json"
	os.remove(POKEDEX_DATA_LOCATION)
	os.rename("out.json", POKEDEX_DATA_LOCATION)

	print("Movedex updated")

def update_learnset():
	print("Updating learnset")
	import src.updaters.learnset_update_script
	
	POKEDEX_DATA_LOCATION = "poke_env/data/learnset.json"
	os.remove(POKEDEX_DATA_LOCATION)
	os.rename("out.json", POKEDEX_DATA_LOCATION)

	print("Learnset updated")