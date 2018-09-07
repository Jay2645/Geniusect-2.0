#!/usr/bin/env python3

from src.helpers import get_id
from src.game_engine.game_calcs import Status
from copy import deepcopy

class Entity:
    """
    This is our version of Showdown's `Effect` class.
    The name was changed for clarity, as "Effect" can have multiple
    interpretations in Pokemon.

    This is essentially a base class for all entities in the game.
    It contains metadata regarding the entity, including its ID,
    name, descriptions, etc.

    Showdown will populate JSON files with these elements, which this
    class can load. Subclasses have more data in their JSON file, so
    subclasses of Entity should override the `from_json` function to
    populate those extra data fields.
    """

    def __init__(self, data, more_data = None, even_more_data = None):
        """
        Initializes this entity.
        :param data: Any extra data that should be appended to this object.
        For example, if we're loading from a JSON file, that JSON file should
        be passed in here.
        """

		# ID. This will be a lowercase version of the name with all the
		# non-alphanumeric characters removed. So, for instance, "Mr. Mime"
		# becomes "mrmime", and "Basculin-Blue-Striped" becomes
		# "basculinbluestriped".
        self.id = ''
        # Name. Currently does not support Unicode letters, so "Flabébé"
		# is "Flabebe" and "Nidoran♀" is "Nidoran-F".
        self.name = ''
        # Full name. Prefixes the name with the effect type. For instance,
		# Leftovers would be "item: Leftovers", confusion the status
		# condition would be "confusion", etc.
        self.full_name = ''
        # Effect type -- "Entity", "Weather", "Status", etc. 
        self.effect_type = 'Entity'
        # Does it exist? Entities can be copied, but only the one actually
        # loaded from Showdown will be marked as being actually existing.
        self.exists = False
        # Dex number? For a Pokemon, this is the National Dex number. For
		# other effects, this is often an internal ID (e.g. a move
		# number). Not all effects have numbers, this will be 0 if it
		# doesn't. Nonstandard effects (e.g. CAP effects) will have
		# negative numbers.
        self.num = 0
        # The generation of Pokemon game this was INTRODUCED (NOT
		# necessarily the current gen being simulated.) Not all effects
		# track generation; this will be 0 if not known.
        self.gen = 0
        # Is this item/move/ability/pokemon unreleased? True if there's
		# no known way to get access to it without cheating.
        self.is_unreleased = False
        # A shortened form of the description of this Entity.
        # Not all Entities have this.
        self.short_description = ''
        # The full description for this effect.
        self.description = ''
        # Is this item/move/ability/pokemon nonstandard? True for effects
		# that have no use in standard formats: made-up pokemon (CAP),
		# glitches (Missingno etc), and Pokestar pokemon.
        self.is_nonstandard = False
        # The duration of this Entity.
        self.duration = None
        # Whether or not the Entity's effect is ignored by Baton Pass.
        self.no_copy = False
        # Whether or not the entity affects fainted Pokemon.
        self.affects_fainted_pkm = False
        # The status that the entity may cause.
        self.status = Status.none
        # The weather that the entity may cause.
        self.weather = ""
        # HP that the entity may drain.
        self.drain = 0
        # Any flags that are associated with this Entity.
        self.flags = {}
        self.source_effect = ''

        # Copy everything over from the data object
        if data is not None:
            if type(data) is dict:
                # Try to load JSON data
                self.from_json(data)
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
            get_id(self.name)
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
    """
    An actual Pokemon Effect. 
    For example, weather effects would be a type of effect.
    """

    def __init__(self, data, more_data = None):
        super().__init__(data, more_data)
        if self.effect_type not in ['Weather', 'Status']:
            self.effect_type = 'Effect'