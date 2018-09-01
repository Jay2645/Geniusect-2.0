#!/usr/bin/env python3

import re
import json
from json import JSONDecodeError

from src.ai.ia import make_best_action, make_best_switch, make_best_move, make_best_order
from src.game_engine.pokemon import Pokemon, Status
from src.game_engine.team import Team
from src.io_process import senders
from src.game_engine.effects import Entity

class Battle(Entity):
    """
    Battle class.
    Unique for each battle.
    Handle everything concerning it.
    """
    def __init__(self, battle_id):
        """
        init Battle method.
        :param battle_id: String, battle_id of battle.
        """
        super().__init__(None)

        self.bot_team = Team()
        self.enemy_team = Team()
        self.current_pkm = None
        self.turn = 0
        self.battle_id = battle_id
        self.player_id = ""
        self.pseudo_weather = []

        print("Battle started")

    async def req_loader(self, jsonobj):
        """
        Parse and translate json send by server. Reload bot team. Called each turn.
        :param req: json sent by server.
        :param websocket: Websocket stream.
        """

        print("Updating Pokemon teams.")

        # Example JSON Object:
        # {
        #   'active':[
        #      {
        #         'moves':[
        #            {
        #               'move':'Flash Cannon',
        #               'id':'flashcannon',
        #               'pp':16,
        #               'maxpp':16,
        #               'target':'normal',
        #               'disabled':False
        #            },
        #            {
        #               'move':'Protect',
        #               'id':'protect',
        #               'pp':16,
        #               'maxpp':16,
        #               'target':'self',
        #               'disabled':False
        #            },
        #            {
        #               'move':'Earth Power',
        #               'id':'earthpower',
        #               'pp':16,
        #               'maxpp':16,
        #               'target':'normal',
        #               'disabled':False
        #            },
        #            {
        #               'move':'Lava Plume',
        #               'id':'lavaplume',
        #               'pp':24,
        #               'maxpp':24,
        #               'target':'allAdjacent',
        #               'disabled':False
        #            }
        #         ]
        #      }
        #   ],
        #   'side':{
        #      'name':'SuchTestBot',
        #      'id':'p1',
        #      'pokemon':[
        #         {
        #            'ident':'p1: Heatran',
        #            'details':'Heatran, L75, M',
        #            'condition':'260/260',
        #            'active':True,
        #            'stats':{
        #               'atk':140,
        #               'def':203,
        #               'spa':239,
        #               'spd':203,
        #               'spe':159
        #            },
        #            'moves':[
        #               'flashcannon',
        #               'protect',
        #               'earthpower',
        #               'lavaplume'
        #            ],
        #            'baseAbility':'flashfire',
        #            'item':'airballoon',
        #            'pokeball':'pokeball',
        #            'ability':'flashfire'
        #         },
        #         {
        #            'ident':'p1: Kingler',
        #            'details':'Kingler, L82, M',
        #            'condition':'224/224',
        #            'active':False,
        #            'stats':{
        #               'atk':260,
        #               'def':236,
        #               'spa':129,
        #               'spd':129,
        #               'spe':170
        #            },
        #            'moves':[
        #               'knockoff',
        #               'liquidation',
        #               'agility',
        #               'rockslide'
        #            ],
        #            'baseAbility':'sheerforce',
        #            'item':'lifeorb',
        #            'pokeball':'pokeball',
        #            'ability':'sheerforce'
        #         },
        #         {
        #            'ident':'p1: Bellossom',
        #            'details':'Bellossom, L83, M',
        #            'condition':'260/260',
        #            'active':False,
        #            'stats':{
        #               'atk':137,
        #               'def':205,
        #               'spa':197,
        #               'spd':214,
        #               'spe':131
        #            },
        #            'moves':[
        #               'sleeppowder',
        #               'moonblast',
        #               'gigadrain',
        #               'hiddenpowerfire60'
        #            ],
        #            'baseAbility':'chlorophyll',
        #            'item':'lifeorb',
        #            'pokeball':'pokeball',
        #            'ability':'chlorophyll'
        #         },
        #         {
        #            'ident':'p1: Froslass',
        #            'details':'Froslass, L83, F',
        #            'condition':'0 fnt',
        #            'active':False,
        #            'stats':{
        #               'atk':137,
        #               'def':164,
        #               'spa':180,
        #               'spd':164,
        #               'spe':230
        #            },
        #            'moves':[
        #               'taunt',
        #               'icebeam',
        #               'destinybond',
        #               'shadowball'
        #            ],
        #            'baseAbility':'cursedbody',
        #            'item':'leftovers',
        #            'pokeball':'pokeball',
        #            'ability':'cursedbody'
        #         },
        #         {
        #            'ident':'p1: Aromatisse',
        #            'details':'Aromatisse, L82, F',
        #            'condition':'210/300',
        #            'active':False,
        #            'stats':{
        #               'atk':123,
        #               'def':165,
        #               'spa':210,
        #               'spd':193,
        #               'spe':95
        #            },
        #            'moves':[
        #               'lightscreen',
        #               'aromatherapy',
        #               'protect',
        #               'moonblast'
        #            ],
        #            'baseAbility':'aromaveil',
        #            'item':'leftovers',
        #            'pokeball':'pokeball',
        #            'ability':'aromaveil'
        #         },
        #         {
        #            'ident':'p1: Gligar',
        #            'details':'Gligar, L79, M',
        #            'condition':'232/232',
        #            'active':False,
        #            'stats':{
        #               'atk':164,
        #               'def':211,
        #               'spa':101,
        #               'spd':148,
        #               'spe':180
        #            },
        #            'moves':[
        #               'earthquake',
        #               'toxic',
        #               'uturn',
        #               'roost'
        #            ],
        #            'baseAbility':'immunity',
        #            'item':'eviolite',
        #            'pokeball':'pokeball',
        #            'ability':'immunity'
        #         }
        #      ]
        #   },
        #   'rqid':16
        #}
        
        self.turn += 2
        objteam = jsonobj['side']['pokemon']
        self.bot_team = Team()

        if "active" in jsonobj.keys():
            self.current_pkm = jsonobj["active"]

        for pkm in objteam:
            try:
                # Load JSON data
                pkm_name = pkm['details'].split(',')[0]
                pkm_condition = pkm['condition']
                pkm_active = pkm['active']
                pkm_level = pkm['details'].split(',')[1].split('L')[1] if len(pkm['details']) > 1 and 'L' in pkm['details'] else 100

                # Create the Pokemon
                newpkm = Pokemon(self, pkm_name, pkm_condition, pkm_active, pkm_level)

                pkm_abilities = [pkm['baseAbility']]
                pkm_item = pkm["item"]
                pkm_stats = pkm['stats']
                pkm_moves = pkm['moves']
                newpkm.load_known(pkm_ability, pkm_item, pkm_stats, pkm_moves)
                self.bot_team.add(newpkm)
            except IndexError as e:
                print("\033[31m" + "IndexError: " + str(e))
                print(pkm + "\033[0m")
                from src.io_process.showdown import Showdown
                login = Showdown()
                login.forfeit_match(self)
                return

        active_pkm = self.bot_team.active()

        # Update our list of moves with metadata about whether they can be used
        if self.current_pkm is not None and active_pkm is not None:
            move_data = self.current_pkm[0]['moves']
            for i in range(len(move_data)):
                for j in range(len(active_pkm.moves)):
                    if active_pkm.moves[j]['id'] is move_data[i]['id']:
                        active_pkm.moves[i]['pp'] = move_data[i]['pp']
                        active_pkm.moves[i]['disabled'] = move_data[i]['disabled']
        print("Our team:")
        print(str(self.bot_team))

        if "forceSwitch" in jsonobj.keys():
            from src.io_process.showdown import Showdown
            login = Showdown()
            await self.make_switch(login.websocket)

    def update_enemy(self, pkm_name, level, condition):
        """
        On first turn, and each time enemy switch, update enemy team and enemy current pokemon.
        :param pkm_name: Pokemon's name
        :param level: int, Pokemon's level
        :param condition: str current_hp/total_hp. /100 if enemy pkm.
        """

        if "-mega" in pkm_name.lower():
            self.enemy_team.remove(pkm_name.lower().split("-mega")[0])
        if "-*" in pkm_name.lower():
            pkm_name = re.sub(r"(.+)-\*", r"\1", pkm_name)
        elif re.compile(r".+-.*").search(pkm_name.lower()):
            try:
                self.enemy_team.remove(re.sub(r"(.+)-.+", r"\1", pkm_name))
            except NameError:
                pass

        # Check to see if the Pokemon is in the enemy team
        if pkm_name not in self.enemy_team:
            # This is a new Pokemon we're seeing
            # Mark all enemy Pokemon as inactive
            for pkm in self.enemy_team.pokemons:
                pkm.active = False
            # Load this new Pokemon with an unknown set of data
            pkm = Pokemon(self, pkm_name, condition, True, level)
            pkm.load_unknown()
            self.enemy_team.add(pkm)
        else:
            # This is a Pokemon we already know about
            for pkm in self.enemy_team.pokemons:
                # Mark this Pokemon as active and the others as inactive
                if pkm.name.lower() == pkm_name.lower():
                    pkm.active = True
                else:
                    pkm.active = False
        print("Enemy team:")
        print(str(self.enemy_team))

    def update_player(self, player_data, player_index):
        if player_data['is_bot']:
            self.player_id = player_data['showdown_id']

    @staticmethod
    def update_status(pokemon, status: str = ""):
        """
        Update status problem.
        :param pokemon: Pokemon.
        :param status: String.
        """
        if status == "tox":
            pokemon.status = Status.toxic
        elif status == "brn":
            pokemon.status = Status.burned
        elif status == "par":
            pokemon.status = Status.paralyzed
        elif status == "psn":
            pokemon.status = Status.poisoned
        elif status == "slp":
            pokemon.status = Status.asleep
        else:
            pokemon.status = Status.healthy

    async def new_turn(self, turn_number):
        print("Beginning turn " + str(turn_number))
        from src.io_process.showdown import Showdown
        login = Showdown()
        websocket = login.websocket
        await self.make_action(websocket)

    @staticmethod
    def set_buff(pokemon, stat, quantity):
        """
        Set buff to pokemon
        :param pokemon: Pokemon
        :param stat: str (len = 3)
        :param quantity: int [-6, 6]
        """
        modifs = {"-6": 1/4, "-5": 2/7, "-4": 1/3, "-3": 2/5, "-2": 1/2, "-1": 2/3, "0": 1, "1": 3/2, "2": 2, "3": 5/2,
                  "4": 3, "5": 7/2, "6": 4}
        buff = pokemon.buff[stat][0] + quantity
        if -6 <= buff <= 6:
            pokemon.buff[stat] = [buff, modifs[str(buff)]]
    
    async def make_team_order(self, websocket):
        """
        Call function to correctly choose the first pokemon to send.
        :param websocket: Websocket stream.
        """
        print("Making team order")

        order = "".join([str(x[0]) for x in make_best_order(self, self.battle_id.split('-')[1])])
        await senders.sendmessage(websocket, self.battle_id, "/team " + order + "|" + str(self.turn))

    async def make_move(self, websocket, best_move=None):
        """
        Call function to send move and use the sendmove sender.
        :param websocket: Websocket stream.
        :param best_move: [int, int] : [id of best move, value].
        """
        if not best_move:
            best_move = make_best_move(self)

        pokemon = self.bot_team.active()
        if best_move[1] == 1024:
            print("Using locked-in move!")
        else:
            print("Using move " + str(pokemon.moves[best_move[0] - 1]['name']))

        best_move_string = str(best_move[0])
        if "canMegaEvo" in self.current_pkm[0]:
            best_move_string = str(best_move[0]) + " mega"
        await senders.sendmove(websocket, self.battle_id, best_move_string, self.turn)

    async def make_switch(self, websocket, best_switch=None):
        """
        Call function to send switch and use the sendswitch sender.
        :param websocket: Websocket stream.
        :param best_switch: int, id of pokemon to switch.
        """
        if not best_switch:
            best_switch = make_best_switch(self)[0]
        if best_switch > 0:
            print("Making a switch to " + self.bot_team.pokemons[best_switch - 1].name)
        else:
            raise RuntimeError("Could not determine a Pokemon to switch to.")
        await senders.sendswitch(websocket, self.battle_id, best_switch, self.turn)

    async def make_action(self, websocket):
        """
        Launch best action chooser and call corresponding functions.
        :param websocket: Websocket stream.
        """
        action = make_best_action(self)
        if action[0] == "move":
            await self.make_move(websocket, action[1:])
        if action[0] == "switch":
            await self.make_switch(websocket, action[1])

    def run_event(self, event_id, target = None, source = None, effect = None, relay_var = True, on_effect = None, fast_exit = None):
        """
        runEvent is the core of Pokemon Showdown's event system.
	    Basic usage
	    ===========

	        run_event('Blah')
	    will trigger any onBlah global event handlers.

	       run_event('Blah', target)
	     will additionally trigger any onBlah handlers on the target, onAllyBlah
	     handlers on any active pokemon on the target's team, and onFoeBlah
	     handlers on any active pokemon on the target's foe's team
	
	       run_event('Blah', target, source)
	     will additionally trigger any onSourceBlah handlers on the source
	
	       run_event('Blah', target, source, effect)
	     will additionally pass the effect onto all event handlers triggered
	
	       run_event('Blah', target, source, effect, relay_var)
	     will additionally pass the relay_var as the first argument along all event
	     handlers
	
	     You may leave any of these null. For instance, if you have a relay_var but
	     no source or effect:
	       run_event('Damage', target, None, None, 50)
	 
	     Event handlers
	     ==============
	 
	     Items, abilities, statuses, and other effects like SR, confusion, weather,
	     or Trick Room can have event handlers. Event handlers are functions that
	     can modify what happens during an event.
	 
	     event handlers are passed:
	       function (target, source, effect)
	     although some of these can be blank.
	 
	     certain events have a relay variable, in which case they're passed:
	       function (relay_var, target, source, effect)
	 
	     Relay variables are variables that give additional information about the
	     event. For instance, the damage event has a relay_var which is the amount
	     of damage dealt.
	 
	     If a relay variable isn't passed to runEvent, there will still be a secret
	     relay_var defaulting to `true`, but it won't get passed to any event
	     handlers.
	 
	     After an event handler is run, its return value helps determine what
	     happens next:
	     1. If the return value isn't None, relay_var is set to the return
	 	    value
	     2. If relay_var is false, no more event handlers are run
	     3. Otherwise, if there are more event handlers, the next one is run and
	 	    we go back to step 1.
	     4. Once all event handlers are run (or one of them results in a false
	 	    relay_var), relay_var is returned by runEvent
	 
	     As a shortcut, an event handler that isn't a function will be interpreted
	     as a function that returns that value.
	 
	     You can have return values mean whatever you like, but in general, we
	     follow the convention that returning `False` means
	     stopping or interrupting the event.
	 
	     For instance, returning `false` from a TrySetStatus handler means that
	     the pokemon doesn't get statused.
	 	 
	     Returning `None` means "don't change anything" or "keep going".
	     A function that does nothing but return `undefined` is the equivalent
	     of not having an event handler at all.
	 
	     Returning a value means that that value is the new `relay_var`. For
	     instance, if a Damage event handler returns 50, the damage event
	     will deal 50 damage instead of whatever it was going to deal before.
        """

    def single_event(self, event_id, effect, effect_data, target, source, source_effect, relay_var = None):

        effect = get_effect(effect)

        has_relay_var = True
        if relay_var is None:
            relay_var = True
            has_relay_var = False