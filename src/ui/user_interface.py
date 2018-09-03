import asyncio
import threading

from tkinter import *

from src.helpers import Singleton, singleton_object
from src.io_process.showdown import create_websocket

@singleton_object
class UserInterface(metaclass=Singleton):
    def __init__(self):
        self.async_loop = None
        self.root = Tk()
        self.entry = Entry(self.root)
        self.entry.grid()

        self.start_showdown = Button(self.root, text='Start Showdown', command=lambda:self.__start_showdown_task(), state="active")
        self.start_showdown.grid()

    def __asyncio_thread(self, async_loop):
        async_loop.run_until_complete(create_websocket())
    
    def __start_showdown_task(self):
        """ Button-Event-Handler starting the asyncio part. """
        self.start_showdown.config(state="disabled")
        threading.Thread(target=self.__asyncio_thread, args=(self.async_loop,)).start()

    def run_tk(self, async_loop):
        self.async_loop = async_loop
        self.root.mainloop()