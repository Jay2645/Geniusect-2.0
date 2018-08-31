#!/usr/bin/env python3

import json
import sys
import re
import requests
import os
import datetime

def update_json(should_force_update = False):
    """
    Update JSON files with the latest from the server
    """

    should_update_json = should_force_update

    if not should_update_json:
        # Check to see when the file was last modified
        last_modification_time = datetime.fromtimestamp(os.stat("data/formats-data.json").st_mtime)
        # If we've already modified today, don't bother updating it
        should_update_json = datetime.today().date() is not last_modification_time.date()
            
    if should_update_json:
        print("Grabbing latest JSON files from the Showdown servers")
    
        os.makedirs("data", exist_ok=True)
        pattern = re.compile(r'([{,])([a-zA-Z0-9-]+):')
        js_pattern = re.compile(r'.+= ')

        formats_url = "https://play.pokemonshowdown.com/data/formats-data.js"
        formats_request = requests.get(formats_url)
        formats = open("data/formats-data.json", "w+", encoding='utf-8')
        # These are Javascript files; we need to get everything between the 
        # equals sign and the first semicolon
        formats_string = re.sub(js_pattern, "", formats_request.text, 1)[:-1]
        formats_string = re.sub(pattern, r'\g<1>"\g<2>":', formats_string)
        # The properties in this string don't have quotes, as this is raw Javascript; let's fix that
        formats.write(formats_string)
        formats.close()
        print("Formats updated")

        moves_url = "https://play.pokemonshowdown.com/data/moves.js"
        moves_request = requests.get(moves_url)
        moves_string = re.sub(js_pattern, "", moves_request.text, 1)[:-1]
        moves_string = re.sub(pattern, r'\g<1>"\g<2>":', moves_string)
        moves = open("data/moves.json", "w+", encoding='utf-8')
        moves.write(moves_string)
        moves.close()
        print("Move list updated")

        pokedex_url = "https://play.pokemonshowdown.com/data/pokedex.js"
        pokedex_request = requests.get(pokedex_url)
        pokedex = open("data/pokedex.json", "w+", encoding='utf-8')
        pokedex_string = re.sub(js_pattern, "", pokedex_request.text, 1)[:-1]
        pokedex_string = re.sub(pattern, r'\g<1>"\g<2>":', pokedex_string)
        pokedex.write(pokedex_string)
        pokedex.close()
        print("Pokedex updated")

        typechart_url = "https://play.pokemonshowdown.com/data/typechart.js"
        typechart_request = requests.get(typechart_url)
        typechart = open("data/typechart.json", "w+", encoding='utf-8')
        typechart_string = re.sub(js_pattern, "", typechart_request.text, 1)[:-1]
        typechart_string = re.sub(pattern, r'\g<1>"\g<2>":', typechart_string)
        typechart.write(typechart_string)
        typechart.close()
        print("Typechart updated")

    load_json()

def load_json():
    print("Validating JSON")

    with open('data/pokedex.json', encoding='utf-8') as pokedex_file:
        pokemon = json.load(pokedex_file)
    print("Pokedex OK")
    with open('data/formats-data.json') as formats_file:
        format_moves = json.load(formats_file)
    print("Battle formats OK")
    with open("data/moves.json") as moves_file:
        moves = json.load(moves_file)
    print("Moves OK")
    with open("data/typechart.json") as typechart_file:
        typechart = json.load(typechart_file)
    print("Typechart OK")
        
    print("All JSON has been loaded!")

def get_move(move_id):

def get_item(item_id):

def get_ability(ability_id):
