.. _basic_concepts:

.. currentmodule:: simpy.core

==============
Basic Concepts
==============

Active components (things that have a behaviour and a state that changes over
time) in SimPy are called *processes*. All processes live in an *environment*.
They interact with the environment and with each other via *events*.

Processes are simple Python `generators
<http://docs.python.org/3/reference/expressions.html#yieldexpr>`_ called
*Process Execution Method (PEM)* in SimPy. During their life time, they create
and ``yield`` events.

When a process yields an event, the process gets *suspended*. SimPy *resumes*
the process, when the event occurs (we say that the event is *activated*). An
event may either *succeed* or *fail*. In the former case, the process is
normally resumed, in the latter case, an exception is thrown into the process.
Multiple processes can wait for the same event. SimPy resumes them in the same
order in which they yielded that event.

There are various types of events. Most of them can be created via the
environment that the process lives in. The most important event type is the
:class:`Timeout`. This event is automatically activated after a specified
amount of (simulation) time and allows a process to hold its state for
that interval.


Our first process
=================

Our first example will be a *car* process. The car will alternately drive and
park for a while. When it starts driving (or parking), it will print the
current simulation time.

So let's start::

    >>> def car(env):
    ...     while True:
    ...         print('Start parking at %d' % env.now)
    ...         parking_duration = 5
    ...         yield env.timeout(parking_duration)
    ...
    ...         print('Start driving at %d' % env.now)
    ...         trip_duration = 2
    ...         yield env.timeout(trip_duration)

Our *car* process requires a reference to an :class:`Environment` ``env`` to
create new events. It also starts an infinite loop which defines the process'
behavior. A process with an infinite loop poses no problem, because the
execution control is passed back to the simulation engine every time the
process yields an event. The engine can then decide whether to resume the
process or not.

As I said before, our car switches between the states *parking* and *driving*.
It announces its new state by printing a message and the current simulation
time (as returned by the :attr:`Environment.now` property). It then calls the
:meth:`Environment.timeout()` factory function to create a :class:`Timeout`,
which is then yielded to hold the current state for some time.

Now that you have written your first PEM, you may want to start the
simulation::

    >>> import simpy
    >>> env = simpy.Environment()
    >>> env.start(car(env))
    Process(car)
    >>> simpy.simulate(env, until=15)
    Start parking at 0
    Start driving at 5
    Start parking at 7
    Start driving at 12
    Start parking at 14

First thing you do is to create an instance of :class:`Environment`. This
instance is passed into our *car* PEM. It also offers
a :meth:`~Environment.start()` method that takes the generator returned by
a PEM and scheduling an initial event for it. *Note: At this time, none of the
code in your PEM is being executed. Calling a PEM just creates a generator
object.* The :class:`Process` returned by :meth:`~Environment.start()` can be
used for process interactions (we will cover that in the next section).
However, you also can just ignore it. Finally, we start the simulation by
calling :func:`simulate()` and passing the environment as well as an end time
to it. You can call this method multiple times for an environment (the end time
should raise with every call, though, else it wouldn't make any sense).


What's next?
============

You should now be familiar with Simpy's terminology and basic concepts. In the
:doc:`next section <process_interaction>`, we will cover process interaction.
