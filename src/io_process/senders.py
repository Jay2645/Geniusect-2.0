#!/usr/bin/env python3

from json import loads
from enum import Flag, auto

class Action(Flag):
    """
    A list of actions we can take.
    Actions can be combined -- you can combine use_move_1 and mega_evolve by
    doing use_move_1 & mega_evolve.
    """
    use_move_1 = auto()
    use_move_2 = auto()
    use_move_3 = auto()
    use_move_4 = auto()
    switch_pokemon_1 = auto()
    switch_pokemon_2 = auto()
    switch_pokemon_3 = auto()
    switch_pokemon_4 = auto()
    switch_pokemon_5 = auto()
    switch_pokemon_6 = auto()
    mega_evolve = auto()
    z_move = auto()

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