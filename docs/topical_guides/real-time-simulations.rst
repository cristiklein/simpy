=====================
Real-time simulations
=====================

Sometimes, you might not want to perform a simulation as fast as possible but
synchronous to the wall-clock time. This kind of simulation is also called
*real-time simulation*.

Real-time simulations may be necessary

- if you have hardware-in-the-loop,
- if there is human interaction with your simulation, or
- if you want to analyze the real-time behavior of an algorithm.

To convert a simulation into a real-time simulation, you only need to replace
SimPy's default :class:`~simpy.core.Environment` with
a :class:`simpy.rt.RealtimeEnvironment`. Apart from the *initial_time*
argument, there are two additional parameters: *factor* and *strict*:
``RealtimeEnvironment(initial_time=0, factor=1.0, strict=True)``.

The *factor* defines how much *real time* passes with each step of simulation
time. By default, this is one second. If you set ``factor=0.1``, a unit of
simulation time will only take a tenth of a second; if you set ``factor=60``,
it will take a minute.

Here is a simple example for converting a normal simulation to a real-time
simulation with a duration of one tenth of a second per simulation time unit:

.. code-block:: python

   >>> import time
   >>> import simpy
   >>>
   >>> def example(env):
   ...     start = time.perf_counter()
   ...     yield env.timeout(1)
   ...     end = time.perf_counter()
   ...     print('Duration of one simulation time unit: %.2fs' % (end - start))
   >>>
   >>> env = simpy.Environment()
   >>> proc = env.process(example(env))
   >>> env.run(until=proc)
   Duration of one simulation time unit: 0.00s
   >>>
   >>> import simpy.rt
   >>> env = simpy.rt.RealtimeEnvironment(factor=0.1)
   >>> proc = env.process(example(env))
   >>> env.run(until=proc)
   Duration of one simulation time unit: 0.10s

If the *strict* parameter is set to ``True`` (the default), the ``step()`` and
``run()`` methods will raise a ``RuntimeError`` if the computation within
a simulation time step take more time than the real-time factor allows. In the
following example, a process will perform a task that takes 0.02 seconds within
a real-time environment with a time factor of 0.01 seconds:

.. code-block:: python

   >>> import time
   >>> import simpy.rt
   >>>
   >>> def slow_proc(env):
   ...     time.sleep(0.02)  # Heavy computation :-)
   ...     yield env.timeout(1)
   >>>
   >>> env = simpy.rt.RealtimeEnvironment(factor=0.01)
   >>> proc = env.process(slow_proc(env))
   >>> try:
   ...     env.run(until=proc)
   ...     print('Everything alright')
   ... except RuntimeError:
   ...     print('Simulation is too slow')
   Simulation is too slow

To suppress the error, simply set ``strict=False``:

.. code-block:: python

   >>> env = simpy.rt.RealtimeEnvironment(factor=0.01, strict=False)
   >>> proc = env.process(slow_proc(env))
   >>> try:
   ...     env.run(until=proc)
   ...     print('Everything alright')
   ... except RuntimeError:
   ...     print('Simulation is too slow')
   Everything alright

That's it. Real-time simulations are that simple with SimPy!
