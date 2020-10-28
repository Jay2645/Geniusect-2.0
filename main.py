#!/usr/bin/env python3

import asyncio

from src.ui.user_interface import UserInterface
from src.io_process.showdown import shutdown_showdown, create_websocket

should_run_headless = False

def main(async_loop):
    """
    Loading function. Connect websocket then launch bot.
    """
    try:
        if should_run_headless:
            async_loop.run_until_complete(create_websocket())
        else:
            ui = UserInterface()
            ui.run_tk(async_loop)
    finally:
        shutdown_showdown()

if __name__ == "__main__":
    main(asyncio.get_event_loop())
