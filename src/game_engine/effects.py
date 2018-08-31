#!/usr/bin/env python3

from src.helpers import string_to_id
from copy import deepcopy

class Entity:

    def __init__(self, data, more_data = None, even_more_data = None):
        self.id = ''
        self.name = ''
        self.full_name = ''
        self.effect_type = 'Entity'
        self.exists = False
        self.num = 0
        self.gen = 0
        self.is_unreleased = False
        self.short_description = ''
        self.description = ''
        self.is_nonstandard = False
        self.duration = None
        self.no_copy = False
        self.affects_fainted_pkm = False
        self.status = ''
        self.weather = ''
        self.drain = ''
        self.flags = {}
        self.source_effect = ''

        # Copy everything over from the data object
        if data is not None:
            if type(data) is str:
                # Try to load JSON data
                from_json(data)
            else:
                self.__dict__.update(data.__dict__)
        if more_data is not None:
            self.__dict__.update(move_data.__dict__)
        if even_more_data is not None:
            self.__dict__.update(even_more_data.__dict__)

        self.name = self.name.strip()
        self.full_name = str(self.full_name)
        if self.full_name is '':
            self.full_name = self.name
        if self.id is '':
            string_to_id(self.name)
        self.effect_type = str(self.effect_type)
        self.exists = self.exists and self.id is not ''

    def from_json(self, json_data):
        try:
            self.id = json_data['id']
        except KeyError:
            pass
        try:
            self.name = json_data['name']
        except KeyError:
            pass
        try:
            self.full_name = json_data['fullname']
        except KeyError:
            pass
        try:
            self.effect_type = json_data['effectType']
        except KeyError:
            pass
        try:
            self.exists = json_data['exists']
        except KeyError:
            pass
        try:
            self.gen = json_data['gen']
        except KeyError:
            pass
        try:
            self.is_unreleased = json_data['isUnreleased']
        except KeyError:
            pass
        try:
            self.short_description = json_data['shortDesc']
        except KeyError:
            pass
        try:
            self.description = json_data['desc']
        except KeyError:
            pass
        try:
            self.is_nonstandard = json_data['isNonstandard']
        except KeyError:
            pass
        try:
            self.duration = json_data['duration']
        except KeyError:
            pass
        try:
            self.no_copy = json_data['noCopy']
        except KeyError:
            pass
        try:
            self.affects_fainted_pkm = json_data['affectsFainted']
        except KeyError:
            pass
        try:
            self.status = json_data['status']
        except KeyError:
            pass
        try:
            self.weather = json_data['weather']
        except KeyError:
            pass
        try:
            self.drain = json_data['drain']
        except KeyError:
            pass
        try:
            self.flags = json_data['flags']
        except KeyError:
            pass
        try:
            self.source_effect = json_data['sourceEffect']
        except KeyError:
            pass

    def __str__(self):
        return self.name

    def get_volatile_copy(self):
        volatile_copy = deepcopy(self)
        volatile_copy.exists = False
        return volatile_copy

class Effect(Entity):
    def __init__(self, data, more_data = None):
        super().__init__(data, more_data)
        if self.effect_type is not in ['Weather', 'Status']:
            self.effect_type = 'Effect'