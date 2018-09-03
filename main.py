#!/usr/bin/env python3.6

import asyncio

from contextlib import suppress

from src.io_process.json_loader import update_json
from src.ui.user_interface import run_tk
from src.io_process.showdown import shutdown_showdown

def main(async_loop):
    """
    Loading function. Connect websocket then launch bot.
    """
    update_json()

    run_tk(async_loop)
    shutdown_showdown()

if __name__ == "__main__":
    main(asyncio.get_event_loop())
