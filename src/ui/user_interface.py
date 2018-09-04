import asyncio
import threading
import queue

from tkinter import *
from tkinter import ttk

from src.helpers import Singleton, singleton_object

class ShowdownWindow(Tk):
    def __init__(self):
        super().__init__()

        self.async_loop = None
        
        self.title("Geniusect 2.0")

        self.showdown_label = Label(self, text="Press the button to initialize a connection to Pokemon Showdown.")
        self.showdown_label.grid(column=1, row=0)

        self.selected_challenge = IntVar()
        challenge_radio_1 = Radiobutton(self, text='Await Challengers', value=0, variable=self.selected_challenge, command=self.__select_radio_button)
        challenge_radio_2 = Radiobutton(self, text='Challenge Player', value=1, variable=self.selected_challenge, command=self.__select_radio_button) 
        challenge_radio_3 = Radiobutton(self, text='Challenge Ladder', value=2, variable=self.selected_challenge, command=self.__select_radio_button)
        challenge_radio_1.grid(column=0, row=1)
        challenge_radio_2.grid(column=1, row=1)
        challenge_radio_3.grid(column=2, row=1)

        self.challenger_name = Entry(self, width=20)
        self.challenger_name.grid(column=1, row=3)
        self.__select_radio_button()

        # @TODO: Avatar

        self.start_showdown = Button(self, text='Start Showdown', command=lambda:self.__start_showdown_task(), state="active")
        self.start_showdown.grid(column=1, row=4)

    def __select_radio_button(self):
        radio_selection = self.selected_challenge.get()
        if radio_selection == 1:
            self.challenger_name.configure(state='normal')
            self.challenger_name.focus()
        else:
            self.challenger_name.configure(state='disabled')

    def __asyncio_thread(self, async_loop):
        from src.io_process.showdown import create_websocket
        async_loop.run_until_complete(create_websocket())
    
    def __start_showdown_task(self):
        """ Button-Event-Handler starting the asyncio part. """
        self.start_showdown.config(state="disabled")
        self.showdown_label.config(text="Connecting to Showdown servers.")
        threading.Thread(target=self.__asyncio_thread, args=(self.async_loop,)).start()


@singleton_object
class UserInterface(metaclass=Singleton):
    def __init__(self):
        self.msg_queue = queue.Queue()
        self.root = ShowdownWindow()
        self.windows = {}

    def get_challenger_name(self):
        return self.root.challenger_name.get()

    def get_selected_challenge_mode(self):
        return self.root.selected_challenge.get()

    def make_new_match(self, match):
        self.msg_queue.put_nowait(match)

    def close_windows(self):
        try:
            self.root.destroy()
        except TclError:
            pass

    def __check_msg_queue(self):
        try:
            # The message queue is a list of matches 
            match = self.msg_queue.get_nowait()
            __create_match_window(match)
        except queue.Empty:
            pass
        # Check again in 200 ms
        self.root.after(200, self.__check_msg_queue)

    def __create_match_window(self, match):
        match_window = Toplevel(self.root)
        match_window.title(match.battle_id)
        self.windows[match.battle_id] = match_window

        
    def on_logged_in(self, username):
        self.root.showdown_label.config(text="Connected to Pokemon Showdown using username " + username)

    def run_tk(self, async_loop):
        self.root.async_loop = async_loop
        self.__check_msg_queue()
        self.root.mainloop()