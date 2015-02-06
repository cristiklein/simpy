======
Events
======

.. currentmodule:: simpy.events

SimPy includes an extensive set of event types for various purposes. All of
them inherit :class:`simpy.events.Event`. The listing below shows the
hierarchy of events built into SimPy::

   events.Event
   ↑
   +— events.Timeout
   |
   +— events.Initialize
   |
   +— events.Process
   |
   +— events.Condition
   |  ↑
   |  +— events.AllOf
   |  |
   |  +— events.AnyOf
   ⋮
   +– [resource events]

This is the set of basic events. Events are extensible and resources, for
example, define additional events. In this guide, we'll focus on the events in
the :mod:`simpy.events` module. The :doc:`guide to resources <resources>`
describes the various resource events.


Event basics
============

SimPy events are very similar – if not identical — to deferreds, futures or
promises. Instances of the class :class:`Event` are used to describe any kind
of events. Events can be in one of the following states. An event

- might happen (not triggered),
- is going to happen (triggered) or
- has happened (processed).

They traverse these states exactly once in that order. Events are also tightly
bound to time and time causes events to advance their state.

Initially, events are not triggered and just objects in memory.

If an event gets triggered, it is scheduled at a given time and inserted into
SimPy's event queue. The property :attr:`Event.triggered` becomes ``True``.

As long as the event is not *processed*, you can add *callbacks* to an event.
Callbacks are callables that accept an event as parameter and are stored in the
:attr:`Event.callbacks` list.

An event becomes *processed* when SimPy pops it from the event queue and
calls all of its callbacks. It is now no longer possible to add callbacks. The
property :attr:`Event.processed` becomes ``True``.

Events also have a *value*. The value can be set before or when the event is
triggered and can be retrieved via :attr:`Event.value` or, within a process, by
yielding the event (``value = yield event``).


Adding callbacks to an event
----------------------------

"What? Callbacks? I've never seen no callbacks!", you might think if you have
worked your way through the :doc:`tutorial <../simpy_intro/index>`.

That's on purpose. The most common way to add a callback to an event is
yielding it from your process function (``yield event``). This will add the
process' *_resume()* method as a callback. That's how your process gets resumed
when it yielded an event.

However, you can add any callable object (function) to the list of callbacks
as long as it accepts an event instance as its single parameter:

.. code-block:: python

   >>> import simpy
   >>>
   >>> def my_callback(event):
   ...     print('Called back from', event)
   ...
   >>> env = simpy.Environment()
   >>> event = env.event()
   >>> event.callbacks.append(my_callback)
   >>> event.callbacks
   [<function my_callback at 0x...>]

If an event has been *processed*, all of its :attr:`Event.callbacks` have been
executed and the attribute is set to ``None``. This is to prevent you from
adding more callbacks – these would of course never get called because the
event has already happened.

Processes are smart about this, though. If you yield a processed event,
*_resume()* will immediately resume your process with the value of the event
(because there is nothing to wait for).


Triggering events
-----------------

When events are triggered, they can either *succeed* or *fail*. For example, if
an event is to be triggered at the end of a computation and everything works
out fine, the event will *succeed*. If an exceptions occurs during that
computation, the event will *fail*.

To trigger an event and mark it as successful, you can use
``Event.succeed(value=None)``. You can optionally pass a *value* to it (e.g.,
the results of a computation).

To trigger an event and mark it as failed, call ``Event.fail(exception)``
and pass an :class:`Exception` instance to it (e.g., the exception you caught
during your failed computation).

There is also a generic way to trigger an event: ``Event.trigger(event)``.
This will take the value and outcome (success or failure) of the event passed
to it.

All three methods return the event instance they are bound to. This allows you
to do things like ``yield Event(env).succeed()``.


Example usages for ``Event``
============================

The simple mechanics outlined above provide a great flexibility in the way
events (even the basic :class:`Event`) can be used.

One example for this is that events can be shared. They can be created by a
process or outside of the context of a process. They can be passed to other
processes and chained:

.. code-block:: python

    >>> class School:
    ...     def __init__(self, env):
    ...         self.env = env
    ...         self.class_ends = env.event()
    ...         self.pupil_procs = [env.process(self.pupil()) for i in range(3)]
    ...         self.bell_proc = env.process(self.bell())
    ...
    ...     def bell(self):
    ...         for i in range(2):
    ...             yield self.env.timeout(45)
    ...             self.class_ends.succeed()
    ...             self.class_ends = self.env.event()
    ...             print()
    ...
    ...     def pupil(self):
    ...         for i in range(2):
    ...             print(' \o/', end='')
    ...             yield self.class_ends
    ...
    >>> school = School(env)
    >>> env.run()
     \o/ \o/ \o/
     \o/ \o/ \o/

This can also be used like the *passivate / reactivate* known from SimPy 2.
The pupils *passivate* when class begins and are *reactivated* when the bell
rings.


Let time pass by: the ``Timeout``
=================================

To actually let time pass in a simulation, there is the *timeout* event.
A timeout has two parameters: a *delay* and an optional *value*:
``Timeout(delay, value=None)``. It triggers itself during its creation and
schedules itself at ``now + delay``. Thus, the ``succeed()`` and ``fail()``
methods cannot be called again and you have to pass the event value to it when
you create the timeout.

The delay can be any kind of number, usually an *int* or *float* as long as it
supports comparison and addition.


Processes are events, too
=========================

SimPy processes (as created by :class:`Process` or ``env.process()``) have the
nice property of being events, too.

That means, that a process can yield another process. It will then be resumed
when the other process ends. The event's value will be the return value of that
process:

.. code-block:: python

    >>> def sub(env):
    ...     yield env.timeout(1)
    ...     return 23
    ...
    >>> def parent(env):
    ...     ret = yield env.process(sub(env))
    ...     return ret
    ...
    >>> env.run(env.process(parent(env)))
    23

The example above will only work in Python >= 3.3. As a workaround for older
Python versions, you can use ``env.exit(23)`` with the same effect.

When a process is created, it schedules an :class:`Initialize` event which will
start the execution of the process when triggered. You usually won't have to
deal with this type of event.

If you don't want a process to start immediately but after a certain delay, you
can use :func:`simpy.util.start_delayed()`. This method returns a helper
process that uses a *timeout* before actually starting a process.

The example from above, but with a delayed start of ``sub()``:

.. code-block:: python

    >>> from simpy.util import start_delayed
    >>>
    >>> def sub(env):
    ...     yield env.timeout(1)
    ...     return 23
    ...
    >>> def parent(env):
    ...     start = env.now
    ...     sub_proc = yield start_delayed(env, sub(env), delay=3)
    ...     assert env.now - start == 3
    ...
    ...     ret = yield sub_proc
    ...     return ret
    ...
    >>> env.run(env.process(parent(env)))
    23


.. _waiting_for_multiple_events_at_once:

Waiting for multiple events at once
===================================

Sometimes, you want to wait for more than one event at the same time. For
example, you may want to wait for a resource, but not for an unlimited amount
of time. Or you may want to wait until all a set of events has happened.

SimPy therefore offers the :class:`AnyOf` and :class:`AllOf` events which both
are a :class:`Condition` event.

Both take a list of events as an argument and are triggered if at least one or
all of them of them are triggered.

.. code-block:: python

    >>> from simpy.events import AnyOf, AllOf, Event
    >>> events = [Event(env) for i in range(3)]
    >>> a = AnyOf(env, events)  # Triggers if at least one of "events" is triggered.
    >>> b = AllOf(env, events)  # Triggers if all each of "events" is triggered.

The value of a condition event is an ordered dictionary with an entry for every
triggered event. In the case of ``AllOf``, the size of that dictionary will
always be the same as the length of the event list. The value dict of ``AnyOf``
will have at least one entry. In both cases, the event instances are used as
keys and the event values will be the values.

As a shorthand for ``AllOf`` and ``AnyOf``, you can also use the logical
operators ``&`` (and) and ``|`` (or):

.. code-block:: python

    >>> def test_condition(env):
    ...     t1, t2 = env.timeout(1, value='spam'), env.timeout(2, value='eggs')
    ...     ret = yield t1 | t2
    ...     assert ret == {t1: 'spam'}
    ...
    ...     t1, t2 = env.timeout(1, value='spam'), env.timeout(2, value='eggs')
    ...     ret = yield t1 & t2
    ...     assert ret == {t1: 'spam', t2: 'eggs'}
    ...
    ...     # You can also concatenate & and |
    ...     e1, e2, e3 = [env.timeout(i) for i in range(3)]
    ...     yield (e1 | e2) & e3
    ...     assert all(e.processed for e in [e1, e2, e3])
    ...
    >>> proc = env.process(test_condition(env))
    >>> env.run()

The order of condition results is identical to the order in which the condition
events were specified. This allows the following idiom for conveniently
fetching the values of multiple events specified in an *and* condition
(including ``AllOf``):

.. code-block:: python

    >>> def fetch_values_of_multiple_events(env):
    ...     t1, t2 = env.timeout(1, value='spam'), env.timeout(2, value='eggs')
    ...     r1, r2 = (yield t1 & t2).values()
    ...     assert r1 == 'spam' and r2 == 'eggs'
    ...
    >>> proc = env.process(fetch_values_of_multiple_events(env))
    >>> env.run()
