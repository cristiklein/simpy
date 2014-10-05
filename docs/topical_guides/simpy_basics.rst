============
SimPy basics
============

This guide describes the basic concepts of SimPy: How does it work? What are
processes, events and the environment? What can I do with them?


How SimPy works
===============

If you break SimPy down, it is just an asynchronous event dispatcher. You
generate events and schedule them at a given simulation time. Events are sorted
by priority, simulation time, and an increasing event id. An event also has
a list of callbacks, which are executed when the event is triggered and
processed by the event loop. Events may also have a return value.

The components involved in this are the :class:`~simpy.core.Environment`,
:mod:`~simpy.events` and the process functions that you write.

Process functions implement your simulation model, that is, they define the
behavior of your simulation. They are plain Python generator functions that
yield instances of :class:`~simpy.events.Event`.

The environment stores these events in its event list and keeps track of the
current simulation time.

If a process function yields an event, SimPy adds the process to the event's
callbacks and suspends the process until the event is triggered and processed.
When a process waiting for an event is resumed, it will also receive the
event's value.

Here is a very simple example that illustrates all this; the code is more
verbose than it needs to be to make things extra clear. You find a compact
version of it at the end of this section::

    >>> import simpy
    >>>
    >>> def example(env):
    ...     event = simpy.events.Timeout(env, delay=1, value=42)
    ...     value = yield event
    ...     print('now=%d, value=%d' % (env.now, value))
    >>>
    >>> env = simpy.Environment()
    >>> example_gen = example(env)
    >>> p = simpy.events.Process(env, example_gen)
    >>>
    >>> env.run()
    now=1, value=42

The ``example()`` process function above first creates
a :class:`~simpy.events.Timeout` event. It passes the environment, a delay, and
a value to it. The Timeout schedules itself at ``now + delay`` (that's why the
environment is required); other event types usually schedule themselves at the
current simulation time.

The process function then yields the event and thus gets suspended. It is
resumed, when SimPy processes the Timeout event. The process function also
receives the event's value (42) -- this is, however, optional, so ``yield
event`` would have been okay if the you were not interested in the value or if
the event had no value at all.

Finally, the process function prints the current simulation time (that is
accessible via the environment's :attr:`~simpy.core.Environment.now` attribute)
and the Timeout's value.

If all required process functions are defined, you can instantiate all objects
for your simulation. In most cases, you start by creating an instance of
:class:`~simpy.core.Environment`, because you'll need to pass it around a lot
when creating everything else.

Starting a process function involves two things:

1. You have to call the process function to create a generator object. (This
   will not execute any code of that function yet. Please read `The Python
   yield keyword explained
   <http://stackoverflow.com/questions/231767/the-python-yield-keyword-explained/231855#231855>`_,
   to understand why this is the case.)

2. You then create an instance of :class:`~simpy.events.Process` and pass the
   environment and the generator object to it. This will schedule an
   :class:`~simpy.events.Initialize` event at the current simulation time which
   starts the execution of the process function. The process instance is also
   an event that is triggered when the process function returns. The
   :doc:`guide to events <events>` explains why this is handy.

Finally, you can start SimPy's event loop. By default, it will run as long as
there are events in the event list, but you can also let it stop earlier by
providing an ``until`` argument (see :ref:`simulation-control`).

The following guides describe the environment and its interactions with events
and process functions in more detail.


"Best practice" version of the example above
============================================

::

    >>> import simpy
    >>>
    >>> def example(env):
    ...     value = yield env.timeout(1, value=42)
    ...     print('now=%d, value=%d' % (env.now, value))
    >>>
    >>> env = simpy.Environment()
    >>> p = env.process(example(env))
    >>> env.run()
    now=1, value=42
