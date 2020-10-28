#!/usr/bin/env python3

from random import randint
from src.ai.ai import AI
from src.io_process import senders
from src.io_process.match import Match

class RandomAI(AI):
    def __init__(self):
        pass

    def make_best_action(self, match : Match) -> senders.Action:
        return senders.int_to_action(randint(1, 26))
