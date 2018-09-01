#!/usr/bin/env python3

import os
import re
import requests
import json

from json import JSONDecodeError
from datetime import datetime
from src.io_process import senders
from src.errors import CantSwitchError, MustSwitchError, BattleCrashedError, NoPokemonError, InvalidMoveError, InvalidTargetError, MegaEvolveError
from src.io_process.login import Login
from src.io_process.battlelog_parsing import battlelog_parsing
from src.game_engine.battle import Battle

nb_fights_max = 20
nb_fights_simu_max = 2
nb_fights = 0
login = Login()

async def filter_server_messages(websocket, message):
    """
    Main in fuction. Filter every message sent by server and launch corresponding function.
    :param websocket: Websocket stream.
    :param message: Message received from server. Format : room|message1|message2.
    """
    lines = message.splitlines()
    battle_id = lines[0].split("|")[0].split(">")[1]
    match = login.check_battle(battle_id)

    for line in lines[1:]:
        try:
            current = line.split('|')
            if current[1] == "init":
                # Creation of the battle
                await login.create_battle(battle_id)
            elif current[1] == "error":
                # Showdown had an error of some kind
                determine_showdown_error(current[2])
            elif current[1] == "player":
                # Gives us info about our current player
                match.set_player_name(current[2], current[3])
            elif current[1] == "teamsize":
                match.set_team_size(current[2], current[3])
            elif current[1] == "gen":
                match.set_generation(current[2])
            elif current[1] == "tier":
                match.set_tier(current[2])
            elif current[1] == "request":
                if current[2] != "":
                    try:
                        request_obj = json.loads(current[2])
                        await match.send_request(request_obj)
                    except JSONDecodeError:
                        print("Could not parse JSON: " + current[2])
                        print("Full context: " + line)
            elif current[1] == "turn":
                await match.new_turn(current[2])
            elif match is not None:
                # Send to battlelog parser.
                battlelog_parsing(match.battle, current[1:])
            else:
                print("Could not parse message: " + line)
        except IndexError:
            pass

def determine_showdown_error(error_reason):
    if "can't switch" in error_reason.lower():
        raise CantSwitchError(error_reason)
    elif "battle crashed" in error_reason.lower():
        raise BattleCrashedError(error_reason)
    elif "do not have a pokémon in slot" in error_reason.lower():
        raise NoPokemonError(error_reason)
    elif "doesn't have a move" in error_reason.lower():
        raise InvalidMoveError(error_reason)
    elif "can't z-move more than once" in error_reason.lower():
        raise InvalidMoveError(error_reason)
    elif "as a z-move" in error_reason.lower():
        raise InvalidMoveError(error_reason)
    elif "needs a target" in error_reason.lower():
        raise InvalidTargetError(error_reason)
    elif "invalid target" in error_reason.lower():
        raise InvalidTargetError(error_reason)
    elif "can't choose a target" in error_reason.lower():
        raise InvalidTargetError(error_reason)
    elif "is disabled" in error_reason.lower():
        raise InvalidMoveError(error_reason)
    elif "mega evolve" in error_reason.lower() or "mega-evolve" in error_reason.lower():
        raise MegaEvolveError(error_reason)
    elif "ultra burst" in error_reason.lower():
        raise MegaEvolveError(error_reason)
    elif "need a switch" in error_reason.lower():
        raise MustSwitchError(error_reason)
    else:
        raise RuntimeError(error_reason)


async def update_json(should_force_update = False):
    """
    Update JSON files with the latest from the server
    """

    should_update_json = should_force_update
    os.makedirs("data", exist_ok=True)

    if not should_update_json:
        # Check to see when the file was last modified
        last_modification_time = datetime.fromtimestamp(os.stat("data/formats-data.json").st_mtime)
        # If we've already modified today, don't bother updating it
        should_update_json = datetime.today().date() != last_modification_time.date()
        if should_update_json:
            print("Going to update JSON. Today is " + str(datetime.today().date()) + " and last modification was done " + str(last_modification_time.date()))

    if should_update_json:
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

    login.load_json()

async def string_to_action(websocket, message):
    """
    First filtering function on received messages.
    Handle challenge and research actions.
    :param websocket: Websocket stream.
    :param message: Message received from server. Format : room|message1|message2.
    """
    global nb_fights_max
    global nb_fights
    global nb_fights_simu_max
    global login

    login.update_websocket(websocket)
    if not login.allow_new_matches:
        exit(2)

    # Handle all meta Showdown stuff related to the bot
    # Login, searching for fights, responding to PMs, etc.
    try:
        string_tab = message.split('|')
        if string_tab[1] == "challstr":
            # If we got the challstr, we can log in.
            await login.log_in(string_tab[2], string_tab[3])
        elif string_tab[1] == "updateuser" and string_tab[2] == login.username:
            await login.search_for_fights()
            if login.challenge_mode == 2:
                nb_fights += 1
        elif string_tab[1] == "deinit" and login.challenge_mode == 2:
            # If previous fight is over and we're searching for battles on our own
            if nb_fights < nb_fights_max:  # If we're below our fight limit
                await senders.searching(websocket, login.formats[0])
                nb_fights += 1
            elif nb_fights >= nb_fights_max and len(login.battles) == 0:  # If we're out of fights
                login.log_out()
        elif "|inactive|Battle timer is ON:" in message and login.challenge_mode == 2:
            # If previous fight has started and we can do more simultaneous fights, start a new fight
            if len(login.battles) < nb_fights_simu_max and nb_fights < nb_fights_max:
                await senders.searching(websocket, login.formats[0])
                nb_fights += 1
        elif "updatechallenges" in string_tab[1]:
            # If somebody challenges the bot
            try:
                if string_tab[2].split('\"')[3] != "challengeTo":
                    if string_tab[2].split('\"')[5] in login.formats:
                        await senders.sender(websocket, "", "/accept " + string_tab[2].split('\"')[3])
                    else:
                        await senders.sender(websocket, "", "/reject " + string_tab[2].split('\"')[3])
                        await senders.sender(websocket, "", "/pm " + string_tab[2].split('\"')[3]
                                             + ", Sorry, I accept only solo randomized metas.")
            except KeyError:
                pass
        elif string_tab[1] == "pm" and "SuchTestBot" not in string_tab[2]:
            if string_tab[4] == ".info":
                await senders.sender(websocket, "", "/pm " + string_tab[2] + ", Showdown Battle Bot. Active for "
                                                                           + ", ".join(login.formats[:-1]) + " and "
                                                                           + login.formats[-1] + ".")
                await senders.sender(websocket, "", "/pm " + string_tab[2] + ", Please challenge me to test your skills.")
            else:
                await senders.sender(websocket, "", "/pm " + string_tab[2] + ", Unknown command, type \".info\" for help.")

        if "battle" in string_tab[0]:
            # Battle concern message.
            await filter_server_messages(websocket, message)
    except Exception as e:
        login.forfeit_all_matches(e)