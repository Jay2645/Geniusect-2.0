#!/usr/bin/env python3

import os
import re
import requests

from src.io_process import senders, json_loader
from src.errors import CantSwitchError, MustSwitchError, BattleCrashedError, NoPokemonError, InvalidMoveError, InvalidTargetError, MegaEvolveError
from src.io_process.showdown import Showdown
from src.io_process.battlelog_parsing import battlelog_parsing
from src.game_engine.battle import Battle

nb_fights_max = 20
nb_fights_simu_max = 2
nb_fights = 0
login = Showdown()

async def filter_server_messages(websocket, message):
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
            elif current[1] == "error":
                determine_showdown_error(current[2])
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
            elif current[1] == "callback":
                try:
                    if current[2] == "trapped":
                        await battle.make_move(websocket)
                    elif current[2] == "cant":
                        if battle.bot_team.active().cant_use_move(current[5]):
                            await battle.make_action(websocket)
                        else:
                            battlelog_parsing(battle, current[1:])
                except KeyError:
                        battlelog_parsing(battle, current[1:])
            elif current[1] == "win":
                await login.game_over(battle)
            elif current[1] == "c":
                # This is a message
                pass
            elif current[1] == "inactive":
                if login.username.lower() in current[2].lower() and "requested by" not in current[2].lower():
                    # We're not active for some reason! Make a move!
                    print("We're inactive!")
                    await battle.make_action(websocket)
            elif current[1] == "error":
                determine_showdown_error(current[2])
            else:
                # Send to battlelog parser.
                battlelog_parsing(battle, current[1:])
        except IndexError:
            pass

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