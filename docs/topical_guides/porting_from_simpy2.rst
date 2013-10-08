.. _porting_from_simpy2:

=========================
Porting from SimPy 2 to 3
=========================


Porting from SimPy 2 to SimPy 3 is not overly complicated. A lot of changes
merely comprise copy/paste.

This guide describes the conceptual and API changes between both SimPy versions
and shows you how to change your code for SimPy 3.


Imports
=======

In SimPy 2, you had to decide at import-time whether you wanted to use a normal
simulation (``SimPy.Simulation``), a real-time simulation
(``SimPy.SimulationRT``) or something else. You usually had to import
``Simulation`` (or ``SimulationRT``), ``Process`` and some of the SimPy
keywords (``hold`` or ``passivate``, for example) from that package.

In SimPy 3, you usually need to import much less classes and modules (e.g., you
don't need direct access to :class:`~simpy.events.Process` and the SimPy
keywords anymore). In most use cases you will now only need to import
:mod:`simpy`.


**SimPy 2**

.. code-block:: python

    from Simpy.Simulation import Simulation, Process, hold


**SimPy 3**

.. code-block:: python

    import simpy


The ``Simulation*`` classes
===========================

SimPy 2 encapsulated the simulation state in a ``Simulation*`` class (e.g.,
``Simulation``, ``SimulationRT`` or ``SimulationTrace``). This
class also had a ``simulate()`` method that executed a normal simulation,
a real-time simulation or something else (depending on the particular class).

There was a global ``Simulation`` instance that was automatically created when
you imported SimPy. You could also instantiate it on your own to uses Simpy's
object-orient API. This led to some confusion and problems, because you had to
pass the ``Simulation`` instance around when you were using the OO API but not
if you were using the procedural API.

In SimPy 3, an :class:`~simpy.core.Environment` replaces ``Simulation`` and
:class:`~simpy.rt.RealtimeEnvironment` replaces ``SimulationRT``. You always
need to instantiate an environment. There's no more global state.

To execute a simulation, you call the environment's
:meth:`~simpy.core.Environment.run()` method.

**SimPy 2**

.. code-block:: python

    # Procedural API
    from SimPy.Simulation import initialize, simulate

    initialize()
    # Start processes
    simulate(until=10)

.. code-block:: python

    # Object-oriented API
    from SimPy.Simulation import Simulation

    sim = Simulation()
    # Start processes
    sim.simulate(until=10)


**SimPy3**

.. code-block:: python

    import simpy

    env = simpy.Environment()
    # Start processes
    env.run(until=10)


Defining a Process
==================

Processes had to inherit the ``Process`` base class in SimPy 2. Subclasses had
to implement at least a so called *Process Execution Method (PEM)* and in
most cases ``__init__()``. Each process needed to know the ``Simulation``
instance it belonged to. This reference was passed implicitly in the procedural
API and had to be passed explicitly in the object-oriented API. Apart from some
internal problems, this made it quite cumbersome to define a simple process.

Processes were started by passing the ``Process`` and the generator returned by
the PEM to either the global ``activate()`` function or the corresponding
``Simulation`` method.

A process in SimPy 3 can be defined by any Python generator function (no matter
if it’s defined on module level or as an instance method). Hence, they are now
just called process functions.  They usually require a reference to the
:class:`~simpy.core.Environment` to interact with, but this is completely
optional.

Processes are can be started by creating a :class:`~simpy.events.Process`
instance and passing the generator to it. The environment provides a shortcut
for this: :meth:`~simpy.core.Environment.process()`.

**SimPy 2**

.. code-block:: python

    # Procedural API
    from Simpy.Simulation import Process

    class MyProcess(Process):
        def __init__(self, another_param):
            super().__init__()
            self.another_param = another_param

        def run(self):
            """Implement the process' behavior."""

    initialize()
    proc = Process('Spam')
    activate(proc, proc.run())


.. code-block:: python

    # Object-oriented API
    from SimPy.Simulation import Simulation, Process

    class MyProcess(Process):
        def __init__(self, sim, another_param):
            super().__init__(sim=sim)
            self.another_param = another_param

        def run(self):
            """Implement the process' behaviour."""

    sim = Simulation()
    proc = Process(sim, 'Spam')
    sim.activate(proc, proc.run())


**SimPy 3**

.. code-block:: python

    import simpy

    def my_process(env, another_param):
        """Implement the process' behavior."""

    env = simpy.Environment()
    proc = env.process(my_process(env, 'Spam'))


SimPy Keywords (``hold`` etc.)
==============================

In SimPy 2, processes created new events by yielding a *SimPy Keyword* and some
additional parameters (at least ``self``). These keywords had to be imported
from ``SimPy.Simulation*`` if they were used. Internally, the keywords were
mapped to a function that generated the according event.

In SimPy 3, you directly yield :mod:`~simpy.events`. You can instantiate an
event directly or use the shortcuts provided by
:class:`~simpy.core.Environment`.

Generally, whenever a process yields an event, this process is suspended and
resumed once the event has been triggered. To motivate this understanding, some
of the events were renamed. For example, the ``hold`` keyword meant to wait
until some time has passed. In terms of events this means that a timeout has
happened. Therefore ``hold`` has been replaced by
a :class:`~simpy.events.Timeout` event.

.. note::

    :class:`~simpy.events.Process` now inherits :class:`~simpy.events.Event`.
    You can thus yield a process to wait until the process terminates.


**SimPy 2**

.. code-block:: python

    yield hold, self, duration
    yield passivate, self
    yield request, self, resource
    yield release, self, resource
    yield waitevent, self, event
    yield waitevent, self, [event_a, event_b, event_c]
    yield queueevent, self, event_list
    yield waituntil, self, cond_func
    yield get, self, level, amount
    yield put, self, level, amount


**SimPy 3**

.. code-block:: python

    from simpy.util import wait_for_any, wait_for_all

    yield env.timeout(duration)        # hold: renamed
    yield env.event()                  # passivate: renamed
    yield resource.request()           # Request is now bound to class Resource
    resource.release()                 # Release no longer needs to be yielded
    yield event                        # waitevent: just yield the event
    yield wait_for_any([event_a, event_b, event_c])  # waitevent
    yield wait_for_all([event_a, event_b, event_c])  # This is new.
    yield event_a | event_b            # Wait for either a or b. This is new.
    yield event_a & event_b            # Wait for a and b. This is new.
    # There is no direct equivalent for "queueevent"
    yield env.process(cond_func(env))  # cond_func is now a process that
                                       # terminates when the cond. is True
                                       # (Yes, you can wait for processes now!)
    yield container.get(amount)        # Level is now called Container
    yield container.put(amount)


Interrupts
==========

In SimPy 2, ``interrupt()`` was a method of the interrupting process. The
victim of the interrupt had to be passed as an argument.

The victim was not directly notified of the interrupt but had to check if the
``interrupted`` flag was set. It then had to reset the interrupt via
``interruptReset()``. You could manually set the ``interruptCause`` attribute
of the victim.

Explicitly checking for an interrupt is obviously error prone as it is too easy
to be forgotten.

In SimPy 3, you call :meth:`~simpy.events.Process.interrupt()` on the victim
process. You can optionally pass a cause. An :exc:`~simpy.events.Interrupt` is
then thrown into the victim process, which has to handle the interrupt via
``try: ... except Interrupt: ...``.


**SimPy 2**

.. code-block:: python

    class Interrupter(Process):
        def __init__(self, victim):
            super().__init__()
            self.victim = victim

        def run(self):
            yield hold, self, 1
            self.interrupt(self.victim_proc)
            self.victim_proc.interruptCause = 'Spam'

    class Victim(Process):
        def run(self):
            yield hold, self, 10
            if self.interrupted:
                cause = self.interruptCause
                self.interruptReset()


**SimPy 3**

.. code-block:: python

    def interrupter(env, victim_proc):
        yield env.timeout(1)
        victim_proc.interrupt('Spam')

    def victim(env):
        try:
            yield env.timeout(10)
        except Interrupt as interrupt:
            cause = interrupt.cause


Conclusion
==========

This guide is by no means complete. If you run into problems, please have
a look at the other :doc:`guides <index>`, the :doc:`examples
<../examples/index>` or the :doc:`../api_reference/index`. You are also very
welcome to submit improvements. Just create a pull request at `bitbucket
<https://bitbucket.org/simpy/simpy/>`_.
