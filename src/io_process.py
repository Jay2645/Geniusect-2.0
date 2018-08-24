#!/usr/bin/env python3

import os
import re
import requests

from src import senders
from src.login import Login
from src.battlelog_parsing import battlelog_parsing
from src.battle import Battle

nb_fights_max = 20
nb_fights_simu_max = 6
nb_fights = 0
login = Login()

formats = [
    "gen7randombattle",
    "gen7monotyperandombattle",
    "gen7hackmonscup",
    "gen7challengecup1v1",
    "gen6battlefactory",
    "gen7bssfactory"
]

async def battle_tag(websocket, message):
    """
    Main in fuction. Filter every message sent by server and launch corresponding function.
    :param websocket: Websocket stream.
    :param message: Message received from server. Format : room|message1|message2.
    """
    lines = message.splitlines()
    battle_id = lines[0].split("|")[0].split(">")[1]
    battle = login.check_battle(battle_id)

    for line in lines[1:]:
        try:
            current = line.split('|')
            if current[1] == "init":
                # Creation of the battle
                await login.create_battle(battle_id)
            elif current[1] == "player" and len(current) > 3 and current[3].lower() == login.username.lower():
                # The bot's turn
                battle.player_id = current[2]
                battle.turn += int(current[2].split('p')[1]) - 1
            elif current[1] == "request":
                # Sent battle JSON
                if len(current[2]) == 1:
                    try:
                        await battle.req_loader(current[3].split('\n')[1], websocket)
                    except KeyError as e:
                        print(e)
                        print(current[3])
                else:
                    await battle.req_loader(current[2], websocket)
            elif current[1] == "teampreview":
                # Select the order of the Pokemon
                await battle.make_team_order(websocket)
            elif current[1] == "turn":
                # Take action (move, switch, etc)
                await battle.make_action(websocket)
            elif current[1] == "callback" and current[2] == "trapped":
                await battle.make_move(websocket)
            elif current[1] == "win":
                await login.game_over(battle)
            elif current[1] == "c":
                # This is a message
                pass
            elif current[1] == "error":
                raise RuntimeError(current[2])
            else:
                # Send to battlelog parser.
                battlelog_parsing(battle, current[1:])
        except IndexError:
            pass

async def update_json():
    """
    Update JSON files with the latest from the server
    """

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
    global battles
    global formats
    global login

    login.update_websocket(websocket)
    try:
        string_tab = message.split('|')
        if string_tab[1] == "challstr":
            # If we got the challstr, we now can log in.
            await login.log_in(string_tab[2], string_tab[3])
        elif string_tab[1] == "updateuser" and string_tab[2] == login.username:
            await login.search_for_fights()
            if login.challenge_mode == 2:
                nb_fights += 1
        elif string_tab[1] == "deinit" and login.challenge_mode == 2:
            # If previous fight is over and we're searching for battles on our own
            if nb_fights < nb_fights_max:  # If we're below our fight limit
                await senders.searching(websocket, formats[0])
                nb_fights += 1
            elif nb_fights >= nb_fights_max and len(battles) == 0:  # If we're out of fights
                login.log_out()
        elif "|inactive|Battle timer is ON:" in message and login.challenge_mode == 2:
            # If previous fight has started and we can do more simultaneous fights, start a new fight
            if len(battles) < nb_fights_simu_max and nb_fights < nb_fights_max:
                await senders.searching(websocket, formats[0])
                nb_fights += 1
        elif "updatechallenges" in string_tab[1]:
            # If somebody challenges the bot
            try:
                if string_tab[2].split('\"')[3] != "challengeTo":
                    if string_tab[2].split('\"')[5] in formats:
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
                                                                           + ", ".join(formats[:-1]) + " and "
                                                                           + formats[-1] + ".")
                await senders.sender(websocket, "", "/pm " + string_tab[2] + ", Please challenge me to test your skills.")
            else:
                await senders.sender(websocket, "", "/pm " + string_tab[2] + ", Unknown command, type \".info\" for help.")

        if "battle" in string_tab[0]:
            # Battle concern message.
            await battle_tag(websocket, message)
    except Exception as e:
        login.forfeit_all_matches(e)
