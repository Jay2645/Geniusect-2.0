#!/usr/bin/env python3

import json
import sys
import re
import requests
import os

from datetime import datetime

from src.helpers import get_id

FORMATS_DATA_PATH = "data/formats-data.json"
MOVES_PATH = "data/moves.json"
POKEDEX_PATH = "data/pokedex.json"
TYPECHART_PATH = "data/typechart.json"

FORMATS_URL = "https://play.pokemonshowdown.com/data/formats-data.js"
MOVES_URL = "https://play.pokemonshowdown.com/data/moves.js"
POKEDEX_URL = "https://play.pokemonshowdown.com/data/pokedex.js"
TYPECHART_URL = "https://play.pokemonshowdown.com/data/typechart.js"

ENCODING = "utf-8"

_pokemon_db = {}
_format_moves_db = {}
_moves_db = {}
_typechart_db = {}

def get_movedex() -> dict:
    return _moves_db

def get_move(id : str) -> dict:
    return get_movedex()[id]

def get_pokedex() -> dict:
    return _pokemon_db

def get_typechart() -> dict:
    return _typechart_db

def get_format_moves() -> dict:
    return _format_moves_db

def update_json(should_force_update : bool = False):
    """
    Update JSON files with the latest from the server
    """

    should_update_json = should_force_update or not os.path.exists(FORMATS_DATA_PATH)

    if not should_update_json:
        # Check to see when the file was last modified
        last_modification_time = datetime.fromtimestamp(os.stat(FORMATS_DATA_PATH).st_mtime)
        # If we've already modified today, don't bother updating it
        should_update_json = datetime.today().date() != last_modification_time.date()
            
    if should_update_json:
        print("Grabbing latest JSON files from the Showdown servers")
    
        os.makedirs("data", exist_ok=True)
        pattern = re.compile(r'([{,])([a-zA-Z0-9-]+):')
        js_pattern = re.compile(r'.+= ')

        formats_request = requests.get(FORMATS_URL)
        formats = open(FORMATS_DATA_PATH, "w+", encoding=ENCODING)
        # These are Javascript files; we need to get everything between the 
        # equals sign and the first semicolon
        formats_string = re.sub(js_pattern, "", formats_request.text, 1)[:-1]
        formats_string = re.sub(pattern, r'\g<1>"\g<2>":', formats_string)
        # The properties in this string don't have quotes, as this is raw Javascript; let's fix that
        formats.write(formats_string)
        formats.close()
        print("Formats updated")

        moves_request = requests.get(MOVES_URL)
        moves_string = re.sub(js_pattern, "", moves_request.text, 1)[:-1]
        moves_string = re.sub(pattern, r'\g<1>"\g<2>":', moves_string)
        _moves_db = open(MOVES_PATH, "w+", encoding=ENCODING)
        _moves_db.write(moves_string)
        _moves_db.close()
        print("Move list updated")

        pokedex_request = requests.get(POKEDEX_URL)
        pokedex = open(POKEDEX_PATH, "w+", encoding=ENCODING)
        pokedex_string = re.sub(js_pattern, "", pokedex_request.text, 1)[:-1]
        pokedex_string = re.sub(pattern, r'\g<1>"\g<2>":', pokedex_string)
        pokedex.write(pokedex_string)
        pokedex.close()
        print("Pokedex updated")

        typechart_request = requests.get(TYPECHART_URL)
        _typechart_db = open(TYPECHART_PATH, "w+", encoding=ENCODING)
        typechart_string = re.sub(js_pattern, "", typechart_request.text, 1)[:-1]
        typechart_string = re.sub(pattern, r'\g<1>"\g<2>":', typechart_string)
        _typechart_db.write(typechart_string)
        _typechart_db.close()
        print("Typechart updated")

    load_json()

def load_json():
    print("Validating JSON")

    global _pokemon_db
    global _format_moves_db
    global _moves_db
    global _typechart_db

    with open(POKEDEX_PATH, encoding=ENCODING) as pokedex_file:
        _pokemon_db = json.load(pokedex_file)
    print("Pokedex OK")
    with open(FORMATS_DATA_PATH) as formats_file:
        _format_moves_db = json.load(formats_file)
    print("Battle formats OK")
    with open(MOVES_PATH) as moves_file:
        _moves_db = json.load(moves_file)
    print("Moves OK")
    with open(TYPECHART_PATH) as typechart_file:
        _typechart_db = json.load(typechart_file)
    print("Typechart OK")
        
    print("All JSON has been loaded!")

def request_loader(server_json : str, battle) -> dict:
    """
    Parse and translate json send by server. Reload bot team. Called each turn.
    :param req: json sent by server.
    :param websocket: Websocket stream.
    """
    jsonobj = json.loads(server_json)
    output = {}

    objteam = team_from_json(jsonobj['side'], battle)
    objteam.is_bot = True

    active_pkm = objteam.active()
    try:
        active_moves = jsonobj['active']
    except KeyError:
        active_moves = None

    # Update our list of moves with metadata about whether they can be used
    if active_moves is not None and active_pkm is not None:
        move_data = active_moves[0]['moves']
        for i in range(len(active_pkm.moves)):
            found_move = False
            for j in range(len(move_data)):
                if active_pkm.moves[i].id == move_data[j]['id']:
                    try:
                        active_pkm.moves[i].disabled = move_data[j]['disabled']
                        active_pkm.moves[i].pp = move_data[j]['pp']
                    except KeyError:
                        # Outrage doesn't take any PP when it's in effect
                        pass
                    found_move = True
                    break
            if not active_pkm.moves[i].disabled:
                # If our move isn't already disabled, disable it if we can't find it
                # Sometimes a disabled move just isn't listed in the active array.
                active_pkm.moves[i].disabled = not found_move

    output['team'] = objteam
    output['active'] = active_moves
    output['turn'] = jsonobj['rqid']
    try:
        output['force_switch'] = jsonobj['forceSwitch']
    except KeyError:
        output['force_switch'] = False
    try:
        output['trapped'] = active_moves[0]['trapped']
    except (KeyError, TypeError):
        output['trapped'] = False

    return output

        
def team_from_json(pkm_team : dict, battle):
    from src.game_engine.pokemon import Pokemon
    from src.game_engine.move import Move
    from src.game_engine.team import Team

    team = Team(battle)
    for pkm in pkm_team["pokemon"]:
        try:
            level = int(pkm['details'].split(',')[1].split('L')[1]) if len(pkm['details']) > 1 and 'L' in pkm['details'] else 100
            newpkm = Pokemon(battle, pkm['details'].split(',')[0], pkm['condition'], pkm['active'], level)
            moveset = []
            for json_move in pkm['moves']:
                move = Move({"id":json_move}, newpkm)
                moveset.append(move)

            newpkm.load_known([pkm['baseAbility']], pkm["item"], pkm['stats'], moveset)
            team.add(newpkm)
        except IndexError:
            pass

    return team

def pokemon_from_json(pokemon_obj) -> dict:
    """
    Filter, regroup and translate data from json files.
    :param pkm_name: Pokemon's name
    :return: Dict. {types, possibleAbilities, baseStats, possibleMoves}
    """
    from src.game_engine.move import Move

    pkm_name = pokemon_obj.name.lower().replace('-', '').replace(' ', '').replace('%', '').replace('\'', '').replace('.', '')

    res = {
        "types": [],
        "possibleAbilities": [],
        "baseStats": {},
        "possibleMoves": []
    }

    current_pokemon = _pokemon_db[pkm_name]
    res["types"] = current_pokemon["types"]
    res["possibleAbilities"] = list(current_pokemon["abilities"].values())
    res["baseStats"] = current_pokemon["baseStats"]
    
    try:
        pokemon_moves = _format_moves_db[pkm_name]["randomBattleMoves"]
    except KeyError:
        if "baseSpecies" in current_pokemon:
            base_species_name = current_pokemon["baseSpecies"].lower()
            pokemon_moves = _format_moves_db[base_species_name]["randomBattleMoves"]
        else:
            raise KeyError("Could not find valid moves for " + pkm_name)
    for json_move in pokemon_moves:
        move = Move({"id":json_move}, pokemon_obj)
        res["possibleMoves"].append(move)
    return res