#!/usr/bin/env python3.6

import asyncio

from src.io_process.json_loader import update_json

should_run_headless = True

def main(async_loop):
    """
    Loading function. Connect websocket then launch bot.
    """
    update_json()

    if should_run_headless:
        from src.io_process.showdown import create_websocket
        async_loop.run_until_complete(create_websocket())
    else:
        from src.ui.user_interface import UserInterface
        from src.io_process.showdown import shutdown_showdown
        ui = UserInterface()
        ui.run_tk(async_loop)
        shutdown_showdown()

if __name__ == "__main__":
    main(asyncio.get_event_loop())
