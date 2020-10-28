#!/usr/bin/env python3

from enum import IntFlag, auto
from json import loads

class Action(IntFlag):
    """
    A list of actions we can take.
    Actions can be combined -- you can combine use_move_1 and mega_evolve by
    doing use_move_1 & mega_evolve.
    """
    use_move_1 = 1
    use_move_2 = 2
    use_move_3 = 4
    use_move_4 = 8
    use_move_1_mega = 17
    use_move_2_mega = 18
    use_move_3_mega = 20
    use_move_4_mega = 24
    use_move_1_z_move = 33
    use_move_2_z_move = 34
    use_move_3_z_move = 36
    use_move_4_z_move = 38
    use_move_1_ultra = 65
    use_move_2_ultra = 66
    use_move_3_ultra = 68
    use_move_4_ultra = 72
    use_move_1_dynamax = 129
    use_move_2_dynamax = 130
    use_move_3_dynamax = 132
    use_move_4_dynamax = 136
    mega_evolve = 16
    z_move = 32
    ultra = 64
    dynamax = 128
    switch_pokemon_1 = 256
    switch_pokemon_2 = 512
    switch_pokemon_3 = 1024
    switch_pokemon_4 = 2048
    switch_pokemon_5 = 4096
    switch_pokemon_6 = 8192

def int_to_action(in_int : int) -> Action:
    if in_int == 1:
        return Action.use_move_1
    elif in_int == 2:
        return Action.use_move_2
    elif in_int == 3:
        return Action.use_move_3
    elif in_int == 4:
        return Action.use_move_4
    elif in_int == 5:
        return Action.switch_pokemon_1
    elif in_int == 6:
        return Action.switch_pokemon_2
    elif in_int == 7:
        return Action.switch_pokemon_3
    elif in_int == 8:
        return Action.switch_pokemon_4
    elif in_int == 9:
        return Action.switch_pokemon_5
    elif in_int == 10:
        return Action.switch_pokemon_6
    elif in_int == 11:
        return Action.use_move_1_dynamax
    elif in_int == 12:
        return Action.use_move_2_dynamax
    elif in_int == 13:
        return Action.use_move_3_dynamax
    elif in_int == 14:
        return Action.use_move_4_dynamax
    elif in_int == 15:
        return Action.use_move_1_ultra
    elif in_int == 16:
        return Action.use_move_2_ultra
    elif in_int == 17:
        return Action.use_move_3_ultra
    elif in_int == 18:
        return Action.use_move_4_ultra
    elif in_int == 19:
        return Action.use_move_1_z_move
    elif in_int == 20:
        return Action.use_move_2_z_move
    elif in_int == 21:
        return Action.use_move_3_z_move
    elif in_int == 22:
        return Action.use_move_4_z_move
    elif in_int == 23:
        return Action.use_move_1_mega
    elif in_int == 24:
        return Action.use_move_2_mega
    elif in_int == 25:
        return Action.use_move_3_mega
    elif in_int == 26:
        return Action.use_move_4_mega

def action_to_str(in_action : Action) -> str:
    if in_action == Action.switch_pokemon_1:
        return "switch 1"
    elif in_action == Action.switch_pokemon_2:
        return "switch 2"
    elif in_action == Action.switch_pokemon_3:
        return "switch 3"
    elif in_action == Action.switch_pokemon_4:
        return "switch 4"
    elif in_action == Action.switch_pokemon_5:
        return "switch 5"
    elif in_action == Action.switch_pokemon_6:
        return "switch 6"

    out_action = "move "
    if Action.use_move_1 in in_action:
        out_action += "1"
    elif Action.use_move_2 in in_action:
        out_action += "2"
    if Action.use_move_3 in in_action:
        out_action += "3"
    elif Action.use_move_4 in in_action:
        out_action += "4"

    if Action.mega_evolve in in_action:
        out_action += " mega"
    elif Action.z_move in in_action:
        out_action += " zmove"
    elif Action.ultra in in_action:
        out_action += " ultra"
    elif Action.dynamax in in_action:
        out_action += " dynamax"

    return out_action


async def sender(websocket, room, message1, message2=None):
    """
    Default websocket sender. Format message and send websocket.
    :param websocket: Websocket stream.
    :param room: Room name.
    :param message1: First part of message.
    :param message2: Second part of message. Optional.
    """
    if message2:
        string = room + '|' + message1 + '|' + message2
    else:
        string = room + '|' + message1

    with open("outlog.txt", "a", encoding='utf-8') as log_file:
        log_file.write("\n" + string)

    print("\nMessage: " + string)

    await websocket.send(string)

async def searching(websocket, form):
    """
    Format search websocket, call sender function.
    :param websocket: Websocket stream.
    :param form: String, battle format.
    """
    await sender(websocket, "", "/search " + form)

async def challenge(websocket, player, form):
    """
    Format challenging websocket, call sender function.
    :param websocket: Websocket stream
    :param player: Player name.
    :param form: String, battle format.
    """
    await sender(websocket, "", "/challenge " + player + ", " + form)

async def sendmessage(websocket, battle_id, message):
    """
    Format text websocket, call sender function.
    :param websocket: Websocket stream.
    :param battle_id: battle_id string.
    :param message: Message to sent.
    """
    await sender(websocket, battle_id, message)

async def sendaction(websocket, battle_id, action : Action, turn):
    """
    Format move choice websocket, call sender function.
    :param websocket: Websocket stream.
    :param battle_id: battle_id string.
    :param move: Move id (1, 2, 3, 4).
    :param turn: Battle turn (1, 2, ...). Different from the one sent by server.
    """
    await sender(websocket, battle_id, "/choose " + action_to_str(action), str(turn))

async def sendmove(websocket, battle_id, move, turn):
    """
    Format move choice websocket, call sender function.
    :param websocket: Websocket stream.
    :param battle_id: battle_id string.
    :param move: Move id (1, 2, 3, 4).
    :param turn: Battle turn (1, 2, ...). Different from the one sent by server.
    """
    await sender(websocket, battle_id, "/choose move " + str(move), str(turn))

async def sendswitch(websocket, battle_id, pokemon, turn):
    """
    Format switch choice websocket, call sender function.
    :param websocket: Websocket stream.
    :param battle_id: battle_id string.
    :param pokemon: Pokemon id (1, 2, 3, 4, 5, 6).
    :param turn: Battle turn (1, 2, ...). Different from the one sent by server.
    """
    await sender(websocket, battle_id, "/choose switch " + str(pokemon), str(turn))

async def leaving(websocket, battle_id):
    """
    Format leaving room websocket, call sender function.
    :param websocket: Websocket stream.
    :param battle_id: battle_id string.
    """
    await sender(websocket, "", "/leave " + battle_id)

async def start_timer(websocket, battle_id):
    """
    Format starting timer websocket, call sender function.
    :param websocket: Websocket stream.
    :param battle_id: battle_id string.
    """
    await sendmessage(websocket, battle_id, "/timer on")

async def forfeit_match(websocket, battle_id):
    """
    Format forfeit game websocket, call sender function.
    :param websocket: Websocket stream.
    :param battle_id: battle_id string.
    """
    await sender(websocket, battle_id, "/forfeit")

async def set_nickname(websocket, username, request_response):
    await sender(websocket, "", "/trn " + username + ",0," + loads(request_response)['assertion'])

async def set_avatar(websocket, avatar_id):
    await sender(websocket, "", "/avatar " + str(avatar_id))