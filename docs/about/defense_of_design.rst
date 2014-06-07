=================
Defense of Design
=================

This document explains why SimPy is designed the way it is and how its design
evolved over time.


Original Design of SimPy 1
==========================

SimPy 1 was heavily inspired by *Simula 67* and *Simscript*. The basic entity
of the framework was a process. A process described a temporal sequence of
actions.

In SimPy 1, you implemented a process by sub-classing ``Process``. The instance
of such a subclass carried both, process and simulation internal information,
whereat the latter wasn't of any use to the process itself. The sequence of
actions of the process was specified in a method of the subclass, called the
*process execution method* (or PEM in short). A PEM interacted with the
simulation by yielding one of several keywords defined in the simulation
package.

The simulation itself was executed via module level functions. The simulation
state was stored in the global scope. This made it very easy to implement and
execute a simulation (despite from heaving to inherit from *Process* and
instantianting the processes before starting their PEMs). However, having all
simulation state global makes it hard to parallelize multiple simulations.

SimPy 1 also followed the "batteries included" approach, providing shared
resources, monitoring, plotting, GUIs and multiple types of simulations
("normal", real-time, manual stepping, with tracing).

The following code fragment shows how a simple simulation could be implemented
in SimPy 1:

.. code-block:: python

    from SimPy.Simulation import Process, hold, initialize, activate, simulate

    class MyProcess(Process):
        def pem(self, repeat):
            for i in range(repeat):
                yield hold, self, 1

    initialize()
    proc = MyProcess()
    activate(proc, proc.pem(3))
    simulate(until=10)



    sim = Simulation()
    proc = MyProcess(sim=sim)
    sim.activate(proc, proc.pem(3))
    sim.simulate(until=10)


Changes in SimPy 2
==================

Simpy 2 mostly sticked with Simpy 1's design, but added an object orient API
for the execution of simulations, allowing them to be executed in parallel.
Since processes and the simulation state were so closely coupled, you now
needed to pass the ``Simulation`` instance into your process to "bind" them to
that instance. Additionally, you still had to activate the process. If you
forgot to pass the simulation instance, the process would use a global instance
thereby breaking your program. SimPy 2's OO-API looked like this:

.. code-block:: python

    from SimPy.Simulation import Simulation, Process, hold

    class MyProcess(Process):
        def pem(self, repeat):
            for i in range(repeat):
                yield hold, self, 1

    sim = Simulation()
    proc = MyProcess(sim=sim)
    sim.activate(proc, proc.pem(3))
    sim.simulate(until=10)


Changes and Decisions in SimPy 3
================================

The original goals for SimPy 3 were to simplify and PEP8-ify its API and to
clean up and modularize its internals. We knew from the beginning that our
goals would not be achievable without breaking backwards compatibility with
SimPy 2. However, we didn't expect the API changes to become as extensive as
they ended up to be.

We also removed some of the included batteries, namely SimPy's plotting and GUI
capabilities, since dedicated libraries like `matplotlib
<http://matplotlib.org/>`_ or `PySide <http://qt-project.org/wiki/PySide>`_ do
a much better job here.

However, by far the most changes are---from the end user's view---mostly
syntactical. Thus, porting from 2 to 3 usually just means replacing a line of
SimPy 2 code with its SimPy3 equivalent (e.g., replacing ``yield hold, self,
1`` with ``yield env.timeout(1)``).

In short, the most notable changes in SimPy 3 are:

- No more sub-classing of ``Process`` required. PEMs can even be simple module
  level functions.
- The simulation state is now stored in an ``Environment`` which can also be
  used by a PEM to interact with the simulation.
- PEMs now yield event objects. This implicates interesting new features and
  allows an easy extension with new event types.

These changes are causing the above example to now look like this:

.. code-block:: python

    from simpy import Environment, simulate

    def pem(env, repeat):
        for i in range(repeat):
            yield env.timeout(i)

    env = Environment()
    env.process(pem(env, 7))
    simulate(env, until=10)

The following sections describe these changes in detail:


No More Sub-classing of ``Process``
-----------------------------------

In Simpy 3, every Python generator can be used as a PEM, no matter if it is
a module level function or a method of an object. This reduces the amount of
code required for simple processes. The ``Process`` class still exists, but you
don't need to instantiate it by yourself, though. More on that later.


Processes Live in an Environment
--------------------------------

Process and simulation state are decoupled. An ``Environment`` holds the
simulation state and serves as base API for processes to create new events.
This allows you to implement advanced use cases by extending the ``Process`` or
``Environment`` class without affecting other components.

For the same reason, the ``simulate()`` method now is a module level function
that takes an environment to simulate.


Stronger Focus on Events
------------------------

In former versions, PEMs needed to yield one of SimPy's built-in keywords (like
``hold``) to interact with the simulation. These keywords had to be imported
separately and were bound to some internal functions that were tightly
integrated with the ``Simulation`` and ``Process`` making it very hard to
extend SimPy with new functionality.

In Simpy 3, PEMs just need to yield events. There are various built-in event
types, but you can also create custom ones by making a subclass of
a ``BaseEvent``. Most events are generated by factory methods of
``Environment``. For example, ``Environment.timeout()`` creates a ``Timeout``
event that replaces the ``hold`` keyword.

The ``Process`` is now also an event. You can now yield another process and
wait for it to finish. For example, think of a car-wash simulation were
"washing" is a process that the car processes can wait for once they enter the
washing station.


Creating Events via the Environment or Resources
------------------------------------------------

The ``Environment`` and resources have methods to create new events, e.g.
``Environment.timeout()`` or ``Resource.request()``. Each of these methods maps
to a certain event type. It creates a new instance of it and returns it, e.g.:

.. code-block:: python

    def event(self):
        return Event()

To simplify things, we wanted to use the event classes directly as methods:

.. code-block:: python

    class Environment(object)
        event = Event

This was, unfortunately, not directly possible and we had to wrap the classes
to behave like bound methods. Therefore, we introduced a ``BoundClass``:

.. code-block:: python

    class BoundClass(object):
        """Allows classes to behave like methods. The ``__get__()`` descriptor
        is basically identical to ``function.__get__()`` and binds the first
        argument of the ``cls`` to the descriptor instance.

        """
        def __init__(self, cls):
            self.cls = cls

        def __get__(self, obj, type=None):
            if obj is None:
                return self.cls
            return types.MethodType(self.cls, obj)


    class Environment(object):
        event = BoundClass(Event)

These methods are called a lot, so we added the event classes as
:data:`types.MethodType` to the instance of ``Environment`` (or the resources,
respectively):

.. code-block:: python

    class Environment(object):
        def __init__(self):
            self.event = types.MethodType(Event, self)

It turned out the the class attributes (the ``BoundClass`` instances) were now
quite useless, so we removed them allthough it was actually the "right" way to
to add classes as methods to another class.
