# -*- coding: utf-8 -*-
"""This module defines the Status class, which represents statuses a pokemon can be
afflicted with.
"""
# pyre-ignore-all-errors[45]
from enum import IntEnum, unique, auto


class Status(IntEnum):
    """Enumeration, represent a status a pokemon can be afflicted with."""

    BRN = auto()
    FNT = auto()
    FRZ = auto()
    PAR = auto()
    PSN = auto()
    SLP = auto()
    TOX = auto()

    def __str__(self) -> str:
        return f"{self.name} (status) object"
