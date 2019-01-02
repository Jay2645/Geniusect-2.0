# Geniusect 2.0

Battle bot for the Pokemon simulator [Pokemon Showdown](http://pokemonshowdown.com). Developed in Python 3.6+

Original bot was forked from [Synedh](https://github.com/Synedh/showdown-battle-bot) and has been heavily modified.

[![No Maintenance Intended](http://unmaintained.tech/badge.svg)](http://unmaintained.tech/)

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

(Python 3.6+ is required)

Once that is set up, set up your bot's Pokemon Showdown username/password in [src/id.txt](src/id.txt). It should be 2 lines; the top line is the username and the bottom line is the password. Eventually, this will be moved to a config file, but for now this is what we're living with.

### How it works
The bot works in four parts: I/O processing, the game engine, the IA, and the user interface.
  
#### I/O Processing
Sends and recieves data from Showdown's servers.  

Showdown uses websockets to send data, therefore this bot uses websockets as well, following the [Pokemon Showdown Protocol](https://github.com/Zarel/Pokemon-Showdown/blob/master/PROTOCOL.md). 

Where it gets tricky is in the connection; the protocol is not very precise. To put it simply, once you connect to the websockets' server, you receive a message formatted like so: `|challstr|<CHALLSTR>`. Then you send a post request to `https://play.pokemonshowdown.com/action.php` with the `<CHALLSTR>` but web-formated (beware of special characters) and the IDs of the bot. Once you get an answer, you have to extract the `assertion` part.

Finally, you have to send a web request in this format : `/trn <USERNAME>,0,<ASSERTION>` where `<USERNAME>` is the username you gave previously and `<ASSERTION>` is what you just extracted.

For more information, check the [showdown.py](src/showdown.py) file. You can also view logs of what Showdown is sending to us in the log.txt file, and logs of what we are sending to Showdown in the outlog.txt file.

#### Game Engine
The game engine simulates battles, teams and Pokemon.

For each battle, an object is created and filled with information sent by Showdown's servers. For the unknown information (enemy's team), moves are filled thanks to a file taken from source code where moves and Pokemon are listed.

Once per day, the bot will create a `data` folder, holding .json files containing information about every single Pokemon. These .json files are taken directly from Showdown's servers, and will be updated every single day after midnight.

#### IA
This is the bots' "brain." It's essentially a series of `if` statements that produce decent results. Each potential action is assigned a score, and then the action with the best score is selected.

Why is it called IA and not AI? I dunno. The name is a holdover from the original fork of the project.

Right now, the bot doesn't think ahead at all. It's hard-coded to look at entry hazards/status effects first, then consider the damage that an attack will do. It'll also think about switching, and will determine if it's worth it to switch in a new Pokemon or if it should just let the current Pokemon die and do a "revenge kill."

Additionally, it doesn't "learn" what set the enemy is using. It assumes that each Pokemon knows all possible Random Battle moves and has all possible abilities. However, if a Pokemon's ability is revealed, or if a Pokemon uses all 4 of their moves, then the bot doesn't get rid of the extras -- it keeps using its initial guess until the end of the game.

In the future, I'd like to expand this module using [Monte Carlo tree search](https://en.wikipedia.org/wiki/Monte_Carlo_tree_search) or [MTD-f](https://en.wikipedia.org/wiki/MTD-f) to play out a series of games to their eventual outcome and take the proper steps. However, before this can be implemented, the Game Engine would need to be improved -- as it stands, many ability effects are hard-coded, and while the most common abilities are accounted for, there are many which don't have proper implementations.

Another future avenue I'd like to take a look at is using TensorFlow to make a Pokemon-playing neutral network. Essentially, it would function similarly to something like the open-source ["Deep Pink"](https://github.com/erikbern/deep-pink) engine, taking data from many games and using them to learn how to play as well as the average player. Pokemon is simpler than something like chess -- there are only 9 possible actions per turn (not including things like Z-Moves or Mega Evolution, which would only affect 1 Pokemon at a time anyhow). Deep Pink uses an 8 \* 8 \* 12-wide layer (8\*8 squares on the board, 12 different types of pieces -- 6 white pieces and 6 black ones). This gets converted to a scalar; we would need to do something similar using variables like Pokemon health, types, abilities, etc. More research would need to be done first, however.

I'd also like to look at moving out of just random battles and making/predicting the opponent's sets in OU or whatever format you so choose, similar to how [Mewtagen](https://github.com/jeffreyscheng/Mewtagen/) works.

#### User Interface
Geniusect has a very simple UI, designed in Tkinter. This UI is mainly used to select which "mode" should be loaded when the bot starts -- should it just sit there and wait for people to sign in to challenge it, should it try to challenge a particular user, or should it attempt to climb the ladder?

The Tkinter UI runs on the main thread, while a separate thread is used to run the actual bot. This is due to the fact that Tkinter is not threadsafe -- the bot uses a queue to communicate with the Tkinter UI when it needs to open new windows and such. Keep this in mind if you are looking to fork this code that the bot will run on a separate thread so long as you keep the UI enabled.

You can also optionally turn on Headless Mode in [main.py](src/main.py). This will enable Geniusect to be run without a UI on devices like servers and such, although you do lose the handy debug info that the UI gives you.

When a game is started, another window will open showing all information the bot knows about the game. You can see all of the bot's Pokemon, their status effects, what moves they know, etc. You can also see what it knows about the enemy team -- all the Pokemon it has seen, as well as all possible Random Battle moves they could know (note that most Pokemon will have more than 4 possible Random Battle moves, so there may be more than 4 moves listed).

Eventually, I'd like this to show estimates about possible EV spreads and natures as well, tying in to Mewtagen-esque predictions from Smogon sets.
