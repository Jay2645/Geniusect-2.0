from src.ai.move_efficiency import effi_move, effi_boost, effi_pkm
from src.game_engine.game_calcs import type_damage_calculation
from src.helpers import player_id_to_index, get_enemy_id_from_player_id

def make_best_order(battle, form=None):
    """
    Parse battle.bot_team to find the best pokemon based on his damages against enemy team.
    :param battle: Battle object, current battle.
    :param form: Battle format.
    :return: List of pokemon in bot_team sorted by efficiency ([[1, 6], [-oo, +oo]]).
    """
    team = battle.teams[player_id_to_index(battle.player_id)]
    enemy_team = battle.teams[get_enemy_id_from_player_id(battle.player_id)]
    ordered_team = []
    for i, pokemon in enumerate(team.pokemon):
        average_efficiency = 0
        for enemy_pkm in enemy_team.pokemon:
            pkm_efficiency = -1024
            if form == 'gen7challengecup1v1':
                for move in pokemon.moves:
                    dmg = effi_move(battle, move, pokemon, enemy_pkm, team)
                    if pkm_efficiency < dmg:
                        pkm_efficiency = dmg
            elif form in ["gen6battlefactory", "gen7bssfactory"]:
                pkm_efficiency = effi_pkm(battle, pokemon, enemy_pkm)
            average_efficiency += pkm_efficiency
        average_efficiency /= 6
        ordered_team.append([i + 1, average_efficiency])
        ordered_team.sort(key=lambda x: x[1], reverse=True)
    return ordered_team


def make_best_switch(battle, force_switch):
    """
    Parse battle.bot_team to find the best pokemon based on his efficiency against current enemy pokemon.
    :param battle: Battle object, current battle.
    :return: (Index of pokemon in bot_team (Integer, [-1, 6]), efficiency (Integer, [0, +oo[))
    """
    print("Looking at our best options to switch")
    team = battle.teams[player_id_to_index(battle.player_id)]
    enemy_pkm = battle.teams[get_enemy_id_from_player_id(battle.player_id)].active()
    best_pkm = None
    effi = -1024
    for pokemon in team.pokemon:
        if pokemon is team.active():
            print("Not switching to " + pokemon.name + " as it is already active")
            continue
        elif pokemon.is_fainted():
            print("Not switching to " + pokemon.name + " as it has fainted")
            continue

        # Entry hazards
        our_effi = effi_pkm(battle, enemy_pkm, pokemon, force_switch)
        print("Raw efficency: " + str(our_effi))
        if team.entry_hazards["stealth_rock"] == 1:
            effi_mod = type_damage_calculation("Rock", pokemon) * 4 # Multiply by 4 so a 4x resist becomes 1
            if effi_mod > 0:
                our_effi /= effi_mod

        ground_effi = type_damage_calculation("Ground", pokemon)
        if ground_effi > 0:
            # Can be affected by ground entry hazards, so let's check if we have any
            if team.entry_hazards["spikes"] > 0:
                our_effi /= (team.entry_hazards["spikes"] * 1.25)
            if team.entry_hazards["sticky_web"] > 0:
                our_effi /= 1.25
            if team.entry_hazards["toxic_spikes"] > 0:
                if "Poison" in pokemon.types:
                    our_effi *= 2 # Poison-types remove Toxic Spikes on entry
                else:
                    poison_effi = type_damage_calculation("Poison", pokemon)
                    if poison_effi > 0:
                        our_effi /= (team.entry_hazards["toxic_spikes"] * 1.25)
        
        print("Looking to switch to " + pokemon.name + ", with an efficiency of " + str(our_effi) + " (best so far: " + str(effi) + ")")
        if our_effi > effi:
            best_pkm = pokemon
            effi = our_effi
    print("Our best switch right now is a switch to " + pokemon.name +", with a weight of " + str(effi))
    try:
        return team.pokemon.index(best_pkm) + 1, effi
    except ValueError:
        return -1, -1024


def make_best_move(battle):
    """
    Parse attacks of current pokemon and send the most efficient based on previous function
    :param battle: Battle object, current battle.
    :return: (Index of move in pokemon (Integer, [-1, 4]), efficiency (Integer, [0, +oo[))
    """
    pokemon_moves = battle.current_pkm[0]["moves"]

    pokemon = battle.teams[player_id_to_index(battle.player_id)].active()
    enemy_team = battle.teams[get_enemy_id_from_player_id(battle.player_id)]
    enemy_pkm = enemy_team.active()
    best_move = (None, -1)

    if len(pokemon_moves) == 1:  # Case Outrage, Mania, Phantom Force, etc.
        print("Locked into " + str(pokemon_moves[0]) + "!")
        return 1, 100

    for i, move in enumerate(pokemon.moves):  # Classical parse
        if move.disabled or move.pp <= 0:
            print("Cannot use " + move.name + " as it is disabled!")
            continue
        effi = effi_move(battle, move, pokemon, enemy_pkm, enemy_team)
        if effi > best_move[1]:
            print(move.name +"'s score of " + str(effi) + " is greater than the previous best (" + str(best_move[1]) + ")")
            best_move = (i + 1, effi)

    return best_move


def make_best_action(battle):
    """
    Global function to choose best action to do each turn.
    Select best action of bot and enemy pokemon, then best pokemon to switch. And finally, chose if it worth or not to
    switch.
    :param battle: Battle object, current battle.
    :return: (Index of move in pokemon (["move"|"switch"], Integer, [-1, 6]))
    """

    best_enm_atk = 0
    best_bot_atk = 0

    bot_pkm = battle.teams[player_id_to_index(battle.player_id)].active()
    enm_pkm = battle.teams[get_enemy_id_from_player_id(battle.player_id)].active()

    if bot_pkm is None:
        raise RuntimeError("We have no active Pokemon")
    elif enm_pkm is None:
        raise RuntimeError("Cannot find any active enemy Pokemon")

    print("Our Pokemon: " + str(bot_pkm))
    print("Enemy Pokemon: " + str(enm_pkm))
    
    # Check our valid moves
    best_move = make_best_move(battle)

    # If we don't have a substitute active, look at our options for switching
    if not bot_pkm.substitute:
        best_switch = make_best_switch(battle, False)    
        if battle.current_pkm is None or best_move[0] is None or best_move[1] < best_switch[1]:
            return "switch", best_switch[0]
    return ["move"] + [i for i in best_move]
