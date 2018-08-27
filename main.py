#!/usr/bin/env python3.6

import asyncio
import websockets
import requests

from src.io_process.io_processing import string_to_action, update_json

async def main():
    """
    Loading function. Connect websocket then launch bot.
    """
    await update_json()

    async with websockets.connect('ws://sim.smogon.com:8000/showdown/websocket') as websocket:
        while True:
            message = await websocket.recv()
            #print("<< {}".format(message))
            await string_to_action(websocket, message)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
