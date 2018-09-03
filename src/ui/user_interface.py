import asyncio
import tkinter
import threading

from src.io_process.showdown import create_websocket

def _asyncio_thread(async_loop):
    async_loop.run_until_complete(create_websocket())
    
def do_tasks(async_loop):
    """ Button-Event-Handler starting the asyncio part. """
    threading.Thread(target=_asyncio_thread, args=(async_loop,)).start()

def run_tk(async_loop):
    root = tkinter.Tk()
    entry = tkinter.Entry(root)
    entry.grid()

    tkinter.Button(root, text='Start Showdown', command=lambda:do_tasks(async_loop)).grid()
    
    root.mainloop()