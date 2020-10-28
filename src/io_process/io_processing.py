#!/usr/bin/env python3
import json
import traceback
import sys

from random import randint
from src.io_process import senders
from src.errors import CantSwitchError, MustSwitchError, BattleCrashedError, NoPokemonError, InvalidMoveError, InvalidTargetError, MegaEvolveError
from src.io_process.showdown import Showdown
from src.ui.user_interface import UserInterface

nb_fights_max = 2
nb_fights_simu_max = 1
nb_fights = 0

login = Showdown()

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
    #if not login.allow_new_matches:
        #exit(2)

    # Handle all meta Showdown stuff related to the bot
    # Login, searching for fights, responding to PMs, etc.
    try:
        string_tab = message.split('|')
        ui = UserInterface()
        challenge_mode = ui.get_selected_challenge_mode()
        if string_tab[1] == "challstr":
            # If we got the challstr, we can log in.
            await login.log_in(string_tab[2], string_tab[3])
        elif string_tab[1] == "updateuser" and string_tab[2] == login.username:
            await login.search_for_fights()
            if challenge_mode == 2:
                nb_fights += 1
        elif string_tab[1] == "deinit" and challenge_mode == 2:
            # If previous fight is over and we're searching for battles on our own
            if nb_fights < nb_fights_max:  # If we're below our fight limit
                await senders.searching(websocket, login.formats[0])
                nb_fights += 1
            elif nb_fights >= nb_fights_max and len(login.battles) == 0:  # If we're out of fights
                login.log_out()
        elif "|inactive|Battle timer is ON:" in message and challenge_mode == 2:
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
            future = await filter_server_messages(websocket, message)
    except Exception as e:
        login.forfeit_all_matches(e)
        print("Caught exception!")
        exc_info = sys.exc_info()
        traceback.print_exception(*exc_info)

async def filter_server_messages(websocket, message):
    """
    Main in function. Filter every message sent by server and launch corresponding function.
    :param websocket: Websocket stream.
    :param message: Message received from server. Format : room|message1|message2.
    """
    global login
    
    lines = message.splitlines()
    battle_id = lines[0].split("|")[0].split(">")[1]

    match = login.check_battle(battle_id)

    should_send_turn = match is not None and match.get_request_id() > 0

    for line in lines[1:]:
        current = line.split('|')
        if current[1] == "init":
            # Creation of the battle
            match = await login.create_battle(battle_id)
        elif current[1] == "turn":
            if match is not None:
                match.new_turn()
                should_send_turn = True
        elif current[1] == "request":
            if match is not None and current[2] != "":
                json_obj = json.loads(current[2])
                match.set_request_id(current[2], json_obj['rqid'])
        elif current[1] == "win":
            # Someone won the game!
            if match is not None:
                should_send_turn = False
                await match.game_is_over(websocket, current[2])
                return
        elif current[1] == "inactive":
            should_send_turn = False

    if should_send_turn:
        match.update_server_message(message)

        print("===========================================================")
        print(match.get_match_state())
        print("===========================================================")

        await senders.sendaction(websocket, battle_id, login.ai.make_best_action(match), match.get_request_id())
        
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