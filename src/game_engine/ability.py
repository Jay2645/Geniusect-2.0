#!/usr/bin/env python3

from src.game_engine.effects import Entity

class Ability(Entity):
    def __init__(self, data, more_data = None):
        super().__init__(data, more_data)
        self.full_name = 'ability: ' + self.name
        self.effect_type = 'Ability'

        # Determine gen
        if self.gen == 0:
            if(self.num >= 192):
                self.gen = 7
            elif(self.num >= 165):
                self.gen = 6
            elif(self.num >= 124):
                self.gen = 5
            elif(self.num >= 77):
                self.gen = 4
            else:
                self.gen = 3