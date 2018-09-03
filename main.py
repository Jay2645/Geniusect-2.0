#!/usr/bin/env python3.6

import asyncio
import websockets
import requests
import tkinter
import threading

from src.io_process.io_processing import string_to_action
from src.io_process.json_loader import update_json
from src.ui.user_interface import run_tk

def main(async_loop):
    """
    Loading function. Connect websocket then launch bot.
    """
    update_json()

    root = tkinter.Tk()
    entry = tkinter.Entry(root)
    entry.grid()
    
    def spawn_ws_listener():
        asyncio.get_event_loop().run_soon(create_websocket())

    tkinter.Button(root, text='Print', command=lambda:do_tasks(async_loop)).grid()
    
    root.mainloop()

def _asyncio_thread(async_loop):
    async_loop.run_until_complete(create_websocket())

def do_tasks(async_loop):
    """ Button-Event-Handler starting the asyncio part. """
    threading.Thread(target=_asyncio_thread, args=(async_loop,)).start()
    
async def create_websocket():
    with open("log.txt", "a", encoding='utf-8') as log_file:
        log_file.write("\n\n\nShowdown Logs:")
        async with websockets.connect('ws://sim.smogon.com:8000/showdown/websocket') as websocket:
            while True:
                message = await websocket.recv()
                #print("<< {}".format(message))
                log_file.write("\nLog: " + message)
                await string_to_action(websocket, message)

if __name__ == "__main__":
    main(asyncio.get_event_loop())
