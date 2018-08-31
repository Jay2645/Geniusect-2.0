#!/usr/bin/env python3

class ShowdownError(RuntimeError):
    pass

class CantSwitchError(ShowdownError):
    pass

class MustSwitchError(ShowdownError):
    pass

class BattleCrashedError(ShowdownError):
    pass

class NoPokemonError(ShowdownError):
    pass

class InvalidMoveError(ShowdownError):
    pass

class InvalidTargetError(ShowdownError):
    pass

class MegaEvolveError(ShowdownError):
    pass
