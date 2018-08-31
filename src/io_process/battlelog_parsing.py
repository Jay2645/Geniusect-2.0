#!/usr/bin/env python3

from src.game_engine.battle import Battle


def major_actions(battle: Battle, split_line):
    if split_line[0] == "move":
        print(split_line[1] + " used " + split_line[2])
        pass
    elif split_line[0] == "switch":
        print(split_line[1] + " came into the battle!")
        if battle.player_id not in split_line[1]:
            battle.update_enemy(split_line[2].split(',')[0], split_line[2].split(',')[1].split('L')[1], split_line[3])
    elif split_line[0] == "swap":
        pass
    elif split_line[0] == "detailschange":
        pass
    elif split_line[0] == "cant":
        pass
    elif split_line[0] == "faint":
        print("A Pokemon fainted! " + split_line[1])
        pass
    elif split_line[0] == "poke":
        if battle.player_id not in split_line[1]:
            pkm = split_line[2].split(', ')
            battle.update_enemy(pkm[0], pkm[1][1:] if len(pkm) > 1 and 'L' in pkm[1] else '100', 100)
    else:
        pass


def minor_actions(battle: Battle, split_line):
    if split_line[0] == "-fail":
        pass
    elif split_line[0] == "-damage":
        if battle.player_id in split_line[1]:
            battle.bot_team.active().update_health(split_line[2])
        else:
            battle.enemy_team.active().update_health(split_line[2])
    elif split_line[0] == "-heal":
        pass
    elif split_line[0] == "-status":
        if battle.player_id in split_line[1]:
            battle.update_status(battle.bot_team.active(), split_line[2])
        else:
            battle.update_status(battle.enemy_team.active(), split_line[2])
    elif split_line[0] == "-curestatus":
        if battle.player_id in split_line[1]:
            battle.update_status(battle.bot_team.active())
        else:
            battle.update_status(battle.enemy_team.active())
    elif split_line[0] == "-cureteam":
        pass
    elif split_line[0] == "-boost":
        if battle.player_id in split_line[1]:
            battle.set_buff(battle.bot_team.active(), split_line[2], int(split_line[3]))
        else:
            battle.set_buff(battle.enemy_team.active(), split_line[2], int(split_line[3]))
    elif split_line[0] == "-unboost":
        if battle.player_id in split_line[1]:
            battle.set_buff(battle.bot_team.active(), split_line[2], - int(split_line[3]))
        else:
            battle.set_buff(battle.enemy_team.active(), split_line[2], - int(split_line[3]))
    elif split_line[0] == "-weather":
        pass
    elif split_line[0] == "-fieldstart":
        pass
    elif split_line[0] == "-fieldend":
        pass
    elif split_line[0] == "-sidestart":
        if "Reflect" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.reflect = True
            else:
                battle.enemy_team.reflect = True
        elif "Light Screen" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.light_screen = True
            else:
                battle.enemy_team.light_screen = True
        elif "Stealth Rock" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.entry_hazards["stealth_rock"] = 1
                print("Sneaky pebbles surround our team!")
            else:
                battle.enemy_team.entry_hazards["stealth_rock"] = 1
                print("Sneaky pebbles surround the enemy team!")
        elif "Toxic Spikes" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.entry_hazards["toxic_spikes"] += 1
                print(str(battle.bot_team.entry_hazards["toxic_spikes"]) + " layers of Toxic Spikes have been added to our side!")
            else:
                battle.enemy_team.entry_hazards["toxic_spikes"] += 1
                print(str(battle.enemy_team.entry_hazards["toxic_spikes"]) + " layers of Toxic Spikes have been added to the enemy side!")
        elif "Spikes" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.entry_hazards["spikes"] += 1
                print(str(battle.bot_team.entry_hazards["spikes"]) + " layers of Spikes have been added to our side!")
            else:
                battle.enemy_team.entry_hazards["spikes"] += 1
                print(str(battle.enemy_team.entry_hazards["spikes"]) + " layers of Spikes have been added to the enemy side!")
        elif "Sticky Web" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.entry_hazards["sticky_web"] = 1
                print("Sticky Web has been added to our side!")
            else:
                battle.enemy_team.entry_hazards["sticky_web"] = 1
                print("Sticky Web has been added to the enemy side!")

    elif split_line[0] == "-sideend":
        if "Reflect" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.reflect = False
            else:
                battle.enemy_team.reflect = False
        elif "Light Screen" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.light_screen = False
            else:
                battle.enemy_team.light_screen = False
        elif "Stealth Rock" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.entry_hazards["stealth_rock"] = 0
                print("Sneaky pebbles are gone from our team!")
            else:
                battle.enemy_team.entry_hazards["stealth_rock"] = 0
                print("Sneaky pebbles are gone from the enemy team!")
        elif "Toxic Spikes" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.entry_hazards["toxic_spikes"] = 0
                print("Toxic Spikes have been removed from our side!")
            else:
                battle.enemy_team.entry_hazards["toxic_spikes"] = 0
                print("Toxic Spikes have been removed from the enemy side!")
        elif "Spikes" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.entry_hazards["spikes"] = 0
                print("Spikes have been removed from our side!")
            else:
                battle.enemy_team.entry_hazards["spikes"] = 0
                print("Spikes have been removed from the enemy side!")
        elif "Sticky Web" in split_line[2]:
            if battle.player_id in split_line[1]:
                battle.bot_team.entry_hazards["sticky_web"] = 0
                print("Sticky Web has been removed from our side!")
            else:
                battle.enemy_team.entry_hazards["sticky_web"] = 0
                print("Sticky Web has been removed from the enemy side!")
    elif split_line[0] == "-crit":
        pass
    elif split_line[0] == "-supereffective":
        pass
    elif split_line[0] == "-resisted":
        pass
    elif split_line[0] == "-immune":
        pass
    elif split_line[0] == "-item":
        if battle.player_id in split_line[1]:
            battle.bot_team.active().item = split_line[2].lower().replace(" ", "")
        else:
            battle.enemy_team.active().item = split_line[2].lower().replace(" ", "")
    elif split_line[0] == "-enditem":
        if battle.player_id not in split_line[1]:
            battle.bot_team.active().item = None
        else:
            battle.enemy_team.active().item = None
    elif split_line[0] == "-ability":
        pass
    elif split_line[0] == "-endability":
        pass
    elif split_line[0] == "-transform":
        pass
    elif split_line[0] == "-mega":
        pass
    elif split_line[0] == "-activate":
        pass
    elif split_line[0] == "-hint":
        pass
    elif split_line[0] == "-center":
        pass
    elif split_line[0] == "-message":
        pass
    elif split_line[0] == "-start":
        if split_line[2].lower() == "substitute":
            if battle.player_id in split_line[1]:
                battle.bot_team.active().substitute = True
            else:
                battle.enemy_team.active().substitute = True
        pass
    elif split_line[0] == "-end":
        if split_line[2].lower() == "substitute":
            if battle.player_id in split_line[1]:
                battle.bot_team.active().substitute = False
            else:
                battle.enemy_team.active().substitute = False
        pass
    else:
        pass


def battlelog_parsing(battle: Battle, split_line):
    print(str(split_line))
    if split_line[0][0] != "-":
        major_actions(battle, split_line)
    else:
        minor_actions(battle, split_line)