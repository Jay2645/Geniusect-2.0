#!/usr/bin/env python3

import json
import sys
import re
import requests
import os

from datetime import datetime

pokemon = {}
format_moves = {}
moves = {}
typechart = {}

def update_json(should_force_update = False):
    """
    Update JSON files with the latest from the server
    """

    should_update_json = should_force_update

    if not should_update_json:
        # Check to see when the file was last modified
        last_modification_time = datetime.fromtimestamp(os.stat("data/formats-data.json").st_mtime)
        # If we've already modified today, don't bother updating it
        should_update_json = datetime.today().date() != last_modification_time.date()
            
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

    global pokemon
    global format_moves
    global moves
    global typechart

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

def request_loader(server_json):
    """
    Parse and translate json send by server. Reload bot team. Called each turn.
    :param req: json sent by server.
    :param websocket: Websocket stream.
    """
    jsonobj = json.loads(server_json)
    output = {}

    objteam = team_from_json(jsonobj['side'])

    active_pkm = objteam.active()
    try:
        active_moves = jsonobj['active']
    except KeyError:
        active_moves = None

    # Update our list of moves with metadata about whether they can be used
    if active_moves is not None and active_pkm is not None:
        move_data = active_moves[0]['moves']
        for i in range(len(move_data)):
            for j in range(len(active_pkm.moves)):
                if active_pkm.moves[j]['id'] == move_data[i]['id']:
                    active_pkm.moves[i]['pp'] = move_data[i]['pp']
                    active_pkm.moves[i]['disabled'] = move_data[i]['disabled']

    output['team'] = objteam
    output['active'] = active_moves
    output['turn'] = jsonobj['rqid']
    try:
        output['force_switch'] = jsonobj['forceSwitch']
    except KeyError:
        output['force_switch'] = False

    return output

        
def team_from_json(pkm_team):
    from src.game_engine.team import Team
    from src.game_engine.pokemon import Pokemon

    team = Team()
    for pkm in pkm_team["pokemon"]:
        try:
            newpkm = Pokemon(pkm['details'].split(',')[0], pkm['condition'], pkm['active'],
                                pkm['details'].split(',')[1].split('L')[1]
                                if len(pkm['details']) > 1 and 'L' in pkm['details'] else 100)
            
            newpkm.load_known([pkm['baseAbility']], pkm["item"], pkm['stats'], pkm['moves'])
            team.add(newpkm)
        except IndexError:
            pass

    return team

def pokemon_from_json(pkm_name):
    """
    Filtrate, regroup and translate data from json files.
    :param pkm_name: Pokemon's name
    :return: Dict. {types, possibleAbilities, baseStats, possibleMoves}
    """

    pkm_name = pkm_name.lower().replace('-', '').replace(' ', '').replace('%', '').replace('\'', '').replace('.', '')
    if pkm_name == 'mimikyubusted':
        pkm_name = 'mimikyu'

    res = {
        "types": [],
        "possibleAbilities": [],
        "baseStats": {},
        "possibleMoves": []
    }

    current_pokemon = pokemon[pkm_name]
    res["types"] = current_pokemon["types"]
    res["possibleAbilities"] = list(current_pokemon["abilities"].values())
    res["baseStats"] = current_pokemon["baseStats"]
    try:
        pokemon_moves = format_moves[pkm_name]["randomBattleMoves"]
    except KeyError:
        raise KeyError("Could not find valid moves for " + pkm_name)
    for move in pokemon_moves:
        res["possibleMoves"].append(moves[move])
    return res