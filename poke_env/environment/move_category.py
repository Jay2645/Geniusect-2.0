# -*- coding: utf-8 -*-
"""This module defines the MoveCategory class, which represents a move category.
"""
# pyre-ignore-all-errors[45]
from enum import IntEnum, unique, auto


class MoveCategory(IntEnum):
    """Enumeration, represent a move category."""

    PHYSICAL = auto()
    SPECIAL = auto()
    STATUS = auto()

    def __str__(self) -> str:
        return f"{self.name} (move category) object"
