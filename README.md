# Geniusect 2.0

Battle bot for the Pokemon simulator [Pokemon Showdown](http://pokemonshowdown.com). Developed in Python 3.6+
Original bot forked from [Synedh](https://github.com/Synedh/showdown-battle-bot)

### Requirements
- asyncio
- websockets
- requests

### Supported formats
- gen7randombattle
- gen7monotyperandombattle
- gen7hackmonscup
- gen7challengecup1v1
- gen6battlefactory
- gen7bssfactory

(More upcoming)

### Installation
```
pip3 install asyncio
pip3 install websockets
pip3 install requests
chmod +x main.py
./main.py
```
(python 3.5+ required)

### How the bot works
The bot works in three parts : I/O process, game engine and IA.
  
#### I/O Process
Sends and recieves data from Showdown's servers.  
Showdown uses websockets to send data, therefore this bot uses websockets as well, following the [Pokemon Showdown Protocol](https://github.com/Zarel/Pokemon-Showdown/blob/master/PROTOCOL.md). 
Tricky part is about connection, the protocol is not very precise about it. To put it simply, once you connect to the websockets' server, you receive a message formatted like so: `|challstr|<CHALLSTR>`. 
Then you send a post request to `https://play.pokemonshowdown.com/action.php` with the `<CHALLSTR>` but web-formated (beware of special characters) and the IDs of the bot.
In the answer, you have to extract the `assertion` part.
Finally, you have to send a web request in this format : `/trn <USERNAME>,0,<ASSERTION>` where `<USERNAME>` is the one you gave previously and `<ASSERTION>` is what you just extracted.
For more information about it, check the [login.py](src/login.py) file.

#### Game Engine
The game engine simulates battles, teams and Pokemon.  
For each battle, an object is created and filled with information sent by Showdown's servers. 
For the unknown information (enemy's team), moves are filled thanks to a file taken from source code where moves and Pokemon are listed.
See [data](data/) forlder for more information.

#### IA
This is the bots' "brain."
At the moment, the IA is static. If you put the bot in the same situation X times, it will act the same way each time.
On each turn, a player (here, the bot) has the choice between switch and use a move.
To choose the move, the bot "just" calculates the efficiency of each move based on base power, stats, typechart, items and abilities.
To choose a Pokemon to switch, the bot will parse all of its Pokemon and calculate its efficiency based on speed and moves power (same calculation as the above).
All the difficulty in building the bot is choosing between using a move and switching out. 
What I mean here is: I (the bot) knows that this Pokemon is dangerous, but is it dangerous enough to switch, or is it better to attack?
Today, this choice is manual. There is a value beyond which the bot switch.
In the long term, I would like to modify this behavior to allow the bot to evolve, based on its previous experiences, but that's hard and I'm missing some knowledge.