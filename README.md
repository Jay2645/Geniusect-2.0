# Geniusect 2.0

Socket battle bot for the Pokemon simulator [Pokemon Showdown](http://pokemonshowdown.com). Developed in Python 3.5+

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

### How does that works
The bot works in three parts : I/O process, game engine and IA.
  
I/O process is about sending and receiving data from Showdown's servers.  
Showdown uses websockets to send data, therefore I use them too. 
Then all I had to do is to follow the [Pokemon Showdown Protocol](https://github.com/Zarel/Pokemon-Showdown/blob/master/PROTOCOL.md). 
Tricky part is about connection, the protocol is not very precise about it.
To be simple, once connected to the websockets' server, you receive a message formated this way : `|challstr|<CHALLSTR>`. 
Then you send a post request to `https://play.pokemonshowdown.com/action.php` with the `<CHALLSTR>` but web-formated (beware of special characters) and the ids of the bot.
In the answer, you have to extract the `assertion` part.
Finally, you have to send a websrequest this format : `/trn <USERNAME>,0,<ASSERTION>` where `<USERNAME>` is the one you gave previously and `<ASSERTION>` the one you extract just before.
For more information about it, check the [login.py](src/login.py) file.

Game engine is about simulating battles, teams and Pokemon.  
For each battle, an object is created and filled with information sent by Showdown's servers. 
For the unknown information (enemy's team), moves are filled thanks to a file taken from source code where moves and Pokemon are listed.
See [data](data/) forlder for more information.

Bot's brain, the IA.  
At the moment I write theses lines, the IA is static. It means if you put the bot in the same situation X times, it will act the same way X times.
On each turn, a player (here, the bot) has the choice between switch and use a move.
To choose the move, the bot "just" calculates the efficiency of each move based on base power, stats, typechart, items and abilities.
To choose a Pokemon to switch, the bot will parse every of its Pokemon and calculate its efficiency based on speed and moves power (same calculation as the above).
All the difficulty in building the bot is choosing between using a move and switching out. 
What I mean here is : I (the bot) know that this Pokemon is dangerous, but is it enough dangerous to switch, or is it more efficient to attack?
Today, this choice is manual. There is a value beyond which the bot switch.
In the long term, I would like to modify this behavior to allow the bot to evolve, based on its previous experiences, but that's hard and I'm missing some knowledge.