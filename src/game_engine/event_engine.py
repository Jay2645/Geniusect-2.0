def run_event(self, event_id, target = None, source = None, effect = None, relay_var = True, on_effect = None, fast_exit = False):
    """
    runEvent is the core of Pokemon Showdown's event system.
	Basic usage
	===========

	run_event('Blah')
	will trigger any onBlah global event handlers.

	run_event('Blah', target)
	will additionally trigger any onBlah handlers on the target, onAllyBlah
	handlers on any active pokemon on the target's team, and onFoeBlah
	handlers on any active pokemon on the target's foe's team
	
	run_event('Blah', target, source)
	will additionally trigger any onSourceBlah handlers on the source
	
	run_event('Blah', target, source, effect)
	will additionally pass the effect onto all event handlers triggered
	
	run_event('Blah', target, source, effect, relay_var)
	will additionally pass the relay_var as the first argument along all event
	handlers
	
	You may leave any of these null. For instance, if you have a relay_var but
	no source or effect:
	run_event('Damage', target, None, None, 50)
	 
	Event handlers
	==============
	 
	Items, abilities, statuses, and other effects like SR, confusion, weather,
	or Trick Room can have event handlers. Event handlers are functions that
	can modify what happens during an event.
	 
	event handlers are passed:
	function (target, source, effect)
	although some of these can be blank.
	 
	certain events have a relay variable, in which case they're passed:
	function (relay_var, target, source, effect)
	 
	Relay variables are variables that give additional information about the
	event. For instance, the damage event has a relay_var which is the amount
	of damage dealt.
	 
	If a relay variable isn't passed to runEvent, there will still be a secret
	relay_var defaulting to `true`, but it won't get passed to any event
	handlers.
	 
	After an event handler is run, its return value helps determine what
	happens next:
	1. If the return value isn't None, relay_var is set to the return
	value
	2. If relay_var is false, no more event handlers are run
	3. Otherwise, if there are more event handlers, the next one is run and
	we go back to step 1.
	4. Once all event handlers are run (or one of them results in a false
	relay_var), relay_var is returned by runEvent
	 
	As a shortcut, an event handler that isn't a function will be interpreted
	as a function that returns that value.
	 
	You can have return values mean whatever you like, but in general, we
	follow the convention that returning `False` means
	stopping or interrupting the event.
	 
	For instance, returning `false` from a TrySetStatus handler means that
	the pokemon doesn't get statused.
	 	 
	Returning `None` means "don't change anything" or "keep going".
	A function that does nothing but return `undefined` is the equivalent
	of not having an event handler at all.
	 
	Returning a value means that that value is the new `relay_var`. For
	instance, if a Damage event handler returns 50, the damage event
	will deal 50 damage instead of whatever it was going to deal before.
    """
    if target is None:
        target = self

    statuses = self.get_relevant_effects(target, "on" + event_id, "onSource" + event_id, source)
    if fast_exit:
        statuses.sort(key=self.compare_redirect_order)
    else:
        statuses.sort(key=self.compare_priority)

    has_relay_var = True
    effect = self.get_effect(effect)

def single_event(self, event_id, effect, effect_data, target, source, source_effect, relay_var = None):
    effect = get_effect(effect)

    has_relay_var = True
    if relay_var is None:
        relay_var = True
        has_relay_var = False