# Geniusect 2.0

Battle bot for the Pokemon simulator [Pokemon Showdown](http://pokemonshowdown.com). Developed in Python 3.6+

Original bot was forked from [Synedh](https://github.com/Synedh/showdown-battle-bot) and has been heavily modified.

[![No Maintenance Intended](http://unmaintained.tech/badge.svg)](http://unmaintained.tech/)

### Requirements
- asyncio
- requests
- aiologger
- tabulate
- websockets>=8.0
- keras_rl==0.4.2
- Keras==2.2.4
- numpy==1.16.2
- tensorflow==1.15.2
- gym==0.12.1
- rl==3.0

Once that is set up, set up your login details in `secrets.cfg`. This file (shouldn't) be tracked -- it's in the .gitignore. If you notice that it's being tracked for whatever reason, run the command `git update-index --skip-worktree secrets.cfg` to keep the file but make it stop appearing in `git status`.
