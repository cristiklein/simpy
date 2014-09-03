================
Shared Resources
================

SimPy offers three types of :mod:`~simpy.resources` that help you modeling
problems, where multiple processes want to use a resource of limited capacity
(e.g., cars at a fuel station with a limited number of fuel pumps) or classical
producer-consumer problems.

In this section, we'll briefly introduce SimPy's
:class:`~simpy.resources.resource.Resource` class.


Basic Resource Usage
====================

We'll slightly modify our electric vehicle process ``car`` that we introduced in
the last sections.

The car will now drive to a *battery charging station (BCS)* and request one of
its two *charging spots*. If both of these spots are currently in use, it waits
until one of them becomes available again. It then starts charging its battery
and leaves the station afterwards::

    >>> def car(env, name, bcs, driving_time, charge_duration):
    ...     # Simulate driving to the BCS
    ...     yield env.timeout(driving_time)
    ...
    ...     # Request one of its charging spots
    ...     print('%s arriving at %d' % (name, env.now))
    ...     with bcs.request() as req:
    ...         yield req
    ...
    ...         # Charge the battery
    ...         print('%s starting to charge at %s' % (name, env.now))
    ...         yield env.timeout(charge_duration)
    ...         print('%s leaving the bcs at %s' % (name, env.now))

The resource's :meth:`~simpy.resources.resource.Resource.request()` method
generates an event that lets you wait until the resource becomes available
again. If you are resumed, you "own" the resource until you *release* it.

If you use the resource with the ``with`` statement as shown above, the
resource is automatically being released. If you call ``request()`` without
``with``, you are responsible to call
:meth:`~simpy.resources.resource.Resource.release()` once you are done using
the resource.

When you release a resource, the next waiting process is resumed and now "owns"
one of the resource's slots. The basic
:class:`~simpy.resources.resource.Resource` sorts waiting processes in a *FIFO
(first in---first out)* way.

A resource needs a reference to an :class:`~simpy.core.Environment` and
a *capacity* when it is created::

    >>> import simpy
    >>> env = simpy.Environment()
    >>> bcs = simpy.Resource(env, capacity=2)

We can now create the ``car`` processes and pass a reference to our resource as
well as some additional parameters to them::

    >>> for i in range(4):
    ...     env.process(car(env, 'Car %d' % i, bcs, i*2, 5))
    <Process(car) object at 0x...>
    <Process(car) object at 0x...>
    <Process(car) object at 0x...>
    <Process(car) object at 0x...>

Finally, we can start the simulation. Since the car processes all terminate on
their own in this simulation, we don't need to specify an *until* time---the
simulation will automatically stop when there are no more events left::

    >>> env.run()
    Car 0 arriving at 0
    Car 0 starting to charge at 0
    Car 1 arriving at 2
    Car 1 starting to charge at 2
    Car 2 arriving at 4
    Car 0 leaving the bcs at 5
    Car 2 starting to charge at 5
    Car 3 arriving at 6
    Car 1 leaving the bcs at 7
    Car 3 starting to charge at 7
    Car 2 leaving the bcs at 10
    Car 3 leaving the bcs at 12

Note that the first two cars can start charging immediately after they arrive
at the BCS, while cars 2 an 3 have to wait.


What's Next
===========

.. The last part of this tutorial will demonstrate, how you can collect data from
.. your simulation.

You should now be familiar with SimPy's basic concepts. The :doc:`next section
<how_to_proceed>` shows you how you can proceed with using SimPy from here on.
