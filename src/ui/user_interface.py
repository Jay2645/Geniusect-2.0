import asyncio
import threading

from tkinter import *
from tkinter import ttk

from src.helpers import Singleton, singleton_object

@singleton_object
class UserInterface(metaclass=Singleton):
    def __init__(self):
        self.async_loop = None
        self.root = Tk()
        self.root.title("Geniusect 2.0")

        self.showdown_label = Label(self.root, text="Press the button to initialize a connection to Pokemon Showdown.")
        self.showdown_label.grid()

        # @TODO: Challenge mode, challenge player, avatar

        self.start_showdown = Button(self.root, text='Start Showdown', command=lambda:self.__start_showdown_task(), state="active")
        self.start_showdown.grid()

    def __asyncio_thread(self, async_loop):
        from src.io_process.showdown import create_websocket
        async_loop.run_until_complete(create_websocket())
    
    def __start_showdown_task(self):
        """ Button-Event-Handler starting the asyncio part. """
        self.start_showdown.config(state="disabled")
        self.showdown_label.config(text="Connecting to Showdown servers.")
        threading.Thread(target=self.__asyncio_thread, args=(self.async_loop,)).start()

    def on_logged_in(self, username):
        self.showdown_label.config(text="Connected to Pokemon Showdown using username " + username)

    def run_tk(self, async_loop):
        self.async_loop = async_loop
        self.root.mainloop()