#!/usr/bin/env python3

# This holds various Exceptions that Showdown can throw.

class ShowdownError(RuntimeError):
    """
    An error that occured from running Pokemon Showdown.
    This gets thrown when Showdown has an issue (for example,
    a server crash).
    It can also be thrown if Showdown doesn't like an action we take.
    """
    pass

class CantSwitchError(ShowdownError):
    """
    This Pokemon can't switch out for whatever reason.
    For example, Arena Trap or Shadow Tag.
    """
    pass

class MustSwitchError(ShowdownError):
    """
    We MUST make a switch operation; we can't try and move.
    """
    pass

class BattleCrashedError(ShowdownError):
    """
    The battle crashed on Showdown's end.
    """
    pass

class NoPokemonError(ShowdownError):
    """
    We can't switch to that Pokemon (i.e. it's fainted).
    """
    pass

class InvalidMoveError(ShowdownError):
    """
    We can't use that move, or there is no move in the given slot.
    """
    pass

class InvalidTargetError(ShowdownError):
    """
    We can't target that Pokemon.
    """
    pass

class MegaEvolveError(ShowdownError):
    """
    We can't Mega-Evolve that Pokemon.
    """
    pass
