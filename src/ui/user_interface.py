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

class PokemonFrame(ttk.Labelframe):
    def __init__(self, master, pokemon):
        super().__init__(master, text=str(pokemon))
        self.pokemon = pokemon
        for i in range(len(pokemon.moves)):
            move = pokemon.moves[i]
            if move is None:
                continue
            move_label = Label(self, text=str(move))
            move_label.grid(column=0, row=i)

class TeamFrame(ttk.Labelframe):
    def __init__(self, master, team, frame_text):
        super().__init__(master, text=frame_text)
        self.pokemon_frames = []
        self.team = team

    def update_team(self, new_team):
        # We generate a new team every turn
        self.team = new_team
        
        for pkm_frame in self.pokemon_frames:
            pkm_frame.destroy()
        self.pokemon_frames = []

        team_pkm = new_team.pokemon

        for i in range(len(team_pkm)):
            pkm_frame = PokemonFrame(self, team_pkm[i])
            pkm_frame.grid(column=i,row=0)
            self.pokemon_frames.append(pkm_frame)

        if len(self.pokemon_frames) < 6:
            for i in range(len(self.pokemon_frames), 6):
                if self.team.is_bot:
                    pkm_label = Label(self, text="None")
                else:
                    pkm_label = Label(self, text="Unknown")
                pkm_label.grid(column=i, row=0)


class BattleWindow(Toplevel):
    def __init__(self, master, match):
        try:
            battle_id = match.battle_id
        except AttributeError:
            return

        super().__init__(master)
        self.match = match
        self.title(battle_id)

        self.plan_label = Label(self, text="No plan yet.")
        self.plan_label.grid(column=0,row=0)

        teams = match.battle.teams
        if teams[0].is_bot:
            self.our_team_frame = TeamFrame(self, teams[0], "Our Team")
            self.enemy_team_frame = TeamFrame(self, teams[1], "Enemy Team")
        else:
            self.our_team_frame = TeamFrame(self, teams[1], "Our Team")
            self.enemy_team_frame = TeamFrame(self, teams[0], "Enemy Team")

        self.our_team_frame.grid(column=0, row=1)
        self.enemy_team_frame.grid(column=0, row=2)

        self.update_teams(match.battle.teams)

    def update_teams(self, teams):
        our_team = teams[0] if teams[0].is_bot else teams[1]
        enemy_team = teams[1] if teams[0].is_bot else teams[0]
        
        self.our_team_frame.update_team(our_team)
        self.enemy_team_frame.update_team(enemy_team)

    def update_plan(self, plan):
        self.plan_label.configure(text=plan)

    def game_over(self):
        self.destroy()
        
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

    def raise_error(self, error):
        self.msg_queue = queue.Queue()
        self.msg_queue.put_nowait(error)

    def make_new_match(self, match):
        self.msg_queue.put_nowait(match)

    def close_windows(self):
        try:
            for window in self.windows:
                self.windows[window].destroy()
            self.root.destroy()
        except TclError:
            pass

    def __check_msg_queue(self):
        try:
            object = self.msg_queue.get_nowait()
            if not self.__create_match_window(object):
                # We can pass exceptions into the queue as well
                self.close_windows()
                raise object
        except queue.Empty:
            pass
        # Check again in 200 ms
        self.root.after(200, self.__check_msg_queue)

    def __create_match_window(self, match):
        try:
            battle_id = match.battle_id
        except AttributeError:
            return False

        match_window = BattleWindow(self.root, match)
        self.windows[battle_id] = match_window
        return True

    def update_plan(self, battle_id, plan):
        try:
            battle_window = self.windows[battle_id]
            battle_window.update_plan(plan)
        except KeyError:
            pass

    def update_team_ui(self, battle_id, teams):
        try:
            battle_window = self.windows[battle_id]
            battle_window.update_teams(teams)
        except KeyError:
            pass

    def match_over(self, battle_id):
        try:
            battle_window = self.windows.pop(battle_id)
            battle_window.game_over()
        except KeyError:
            pass

    def on_logged_in(self, username):
        self.root.showdown_label.config(text="Connected to Pokemon Showdown using username " + username)

    def run_tk(self, async_loop):
        self.root.async_loop = async_loop
        self.__check_msg_queue()
        self.root.mainloop()