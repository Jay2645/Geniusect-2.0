import asyncio
import tkinter
import threading

from src.io_process.showdown import create_websocket

class UserInterface():
    def __init__(self, async_loop):
        self.root = tkinter.Tk()
        self.entry = tkinter.Entry(self.root)
        self.entry.grid()

        self.start_showdown = tkinter.Button(self.root, text='Start Showdown', command=lambda:self.do_tasks(async_loop)).grid()

    def _asyncio_thread(self, async_loop):
        async_loop.run_until_complete(create_websocket())
    
    def do_tasks(self, async_loop):
        """ Button-Event-Handler starting the asyncio part. """
        threading.Thread(target=self._asyncio_thread, args=(async_loop,)).start()

    def run_tk(self):
        self.root.mainloop()