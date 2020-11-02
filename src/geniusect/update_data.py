#!/usr/bin/env python3

import os
import logging

def update_pokedex():
	print("Updating Pokedex")
	import src.updaters.pokedex_update_script
	
	POKEDEX_DATA_LOCATION = "poke_env/data/pokedex.json"
	try:
		os.remove(POKEDEX_DATA_LOCATION)
	except FileNotFoundError:
		pass
	os.rename("out.json", POKEDEX_DATA_LOCATION)

	print("Pokedex updated")

def update_itemdex():
	print("Updating Itemdex")
	import src.updaters.itemdex_update_script
	
	ITEMDEX_DATA_LOCATION = "poke_env/data/items.json"
	try:
		os.remove(ITEMDEX_DATA_LOCATION)
	except FileNotFoundError:
		pass
	os.rename("out.json", ITEMDEX_DATA_LOCATION)

	print("Itemdex updated")

def update_movedex():
	print("Updating Movedex")
	import src.updaters.move_update_script
	
	MOVEDEX_DATA_LOCATION = "poke_env/data/moves.json"
	try:
		os.remove(MOVEDEX_DATA_LOCATION)
	except FileNotFoundError:
		pass
	os.rename("out.json", MOVEDEX_DATA_LOCATION)

	print("Movedex updated")

def update_learnset():
	print("Updating learnset")
	import src.updaters.learnset_update_script
	
	LEARNSET_DATA_LOCATION = "poke_env/data/learnset.json"
	try:
		os.remove(LEARNSET_DATA_LOCATION)
	except FileNotFoundError:
		pass
	os.rename("out.json", LEARNSET_DATA_LOCATION)

	print("Learnset updated")