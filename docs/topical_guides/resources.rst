================
Shared Resources
================

Shared resources are another way to model :doc:`process_interaction`. They form
a congestion point where processes queue up in order to use them.

SimPy defines three categories of resources:

- :ref:`res_type_resource` – Resources that can be used by a limited
  number of processes at a time (e.g., a gas station with a limited number of
  fuel pumps).

- :ref:`res_type_container` – Resources that model the production and
  consumption of a homogeneous, undifferentiated bulk. It may either be
  continuous (like water) or discrete (like apples).

- :ref:`res_type_store` – Resources that allow the production and
  consumption of Python objects.


The basic concept of resources
==============================

All resources share the same basic concept: The resource itself is some kind of
a container with a, usually limited, *capacity*. Processes can either try to
*put* something into the resource or try to *get* something out. If the
resource is full or empty, they have to *queue* up and wait.

This is roughly, how every resource looks like::

   BaseResource(capacity):
      put_queue
      get_queue

      put(): event
      get(): event

Every resources a maximum capacity and two queues, one for processes that want
to put something into it and one for processes that want to get something out.
The ``put()`` and ``get()`` methods both return an event that is triggered when
the corresponding action was successful.


Resources and interrupts
------------------------

While a process is waiting for a put or get event to succeed, it may be
:ref:`interrupted <interrupting-another-process>` by another process. After
catching the interrupt, the process has two possibilities:

1. It may continue to wait for the request (by yielding the event again).

2. It may stop waiting for the request. In this case, it has to call the
   event's ``cancel()`` method.

   Since you can easily forget this, all resources events are *context
   managers* (see the `Python docs
   <https://docs.python.org/3/reference/compound_stmts.html#with>`_ for
   details).

---------

The resource system is modular and extensible. Resources can, for example, use
specialized queues and event types. This allows them to use sorted queues, to
add priorities to events, or to offer preemption.


.. _res_type_resource:

Resources
=========

.. currentmodule:: simpy.resources.resource

Resources can be used by a limited number of processes at a time (e.g.,
a gas station with a limited number of fuel pumps). Processes *request* these
resources to become a user (or to "own" them) and have to *release* them once
they are done (e.g., vehicles arrive at the gas station, use a fuel-pump, if
one is available, and leave when they are done).

Requesting a resources is modeled as "putting a process' token into the
resources" and releasing a resources correspondingly as "getting a process'
token out of the resource". Thus, calling ``request()``/``release()`` is
equivalent to calling ``put()``/``get()``. Releasing a resource will always
succeed immediately.

SimPy implements three *resource* types:

1. :class:`Resource`
2. :class:`PriorityResource`, where queueing processes are sorted by priority
3. :class:`PreemptiveResource`, where processes additionally may preempt other
   processes with a lower priority


Resource
--------

The ``Resource`` is conceptually a *semaphore*. Its only parameter – apart from
the obligatory reference to an :class:`~simpy.core.Environment` – is its
*capacity*. It must be a positive number and defaults to 1: ``Resource(env,
capacity=1)``.

Instead of just counting its current users, it stores the request event as an
"access token" for each user. This is, for example, useful for adding
preemption (see below).

Here is as basic example for using a resource:

.. code-block:: python

   >>> import simpy
   >>>
   >>> def resource_user(env, resource):
   ...     request = resource.request()  # Generate a request event
   ...     yield request                 # Wait for access
   ...     yield env.timeout(1)          # Do something
   ...     resource.release(request)     # Release the resource
   ...
   >>> env = simpy.Environment()
   >>> res = simpy.Resource(env, capacity=1)
   >>> user = env.process(resource_user(env, res))
   >>> env.run()

Note, that you have to release the resource under all conditions; for example,
if you got interrupted while waiting for or using the resource. In order to
help you with that and to avoid too many ``try: ... finally: ...`` constructs,
request events can be used as context manager:

.. code-block:: python

   >>> def resource_user(env, resource):
   ...     with resource.request() as req:  # Generate a request event
   ...         yield req                    # Wait for access
   ...         yield env.timeout(1)         # Do something
   ...                                      # Resource released automatically
   >>> user = env.process(resource_user(env, res))
   >>> env.run()

Resources allow you retrieve the list of users and queued as well as the
number of users and resource's capacity:

.. code-block:: python

   >>> res = simpy.Resource(env, capacity=1)
   >>>
   >>> def print_stats(res):
   ...     print('%d of %d slots are allocated.' % (res.count, res.capacity))
   ...     print('  Users:', res.users)
   ...     print('  Queued events:', res.queue)
   >>>
   >>>
   >>> def user(res):
   ...     print_stats(res)
   ...     with res.request() as req:
   ...         yield req
   ...         print_stats(res)
   ...     print_stats(res)
   >>>
   >>> procs = [env.process(user(res)), env.process(user(res))]
   >>> env.run()
   0 of 1 slots are allocated.
     Users: []
     Queued events: []
   1 of 1 slots are allocated.
     Users: [<Request() object at 0x...>]
     Queued events: []
   1 of 1 slots are allocated.
     Users: [<Request() object at 0x...>]
     Queued events: [<Request() object at 0x...>]
   0 of 1 slots are allocated.
     Users: []
     Queued events: [<Request() object at 0x...>]
   1 of 1 slots are allocated.
     Users: [<Request() object at 0x...>]
     Queued events: []
   0 of 1 slots are allocated.
     Users: []
     Queued events: []


PriorityResource
----------------

As you may know from the real world, not every one is equally important. To map
that to SimPy, there's the *PriorityResource*. This subclass of *Resource* lets
requesting processes provide a priority for each request. More important
requests will gain access to the resource earlier than less important ones.
Priority is expressed by integer numbers; smaller numbers mean a higher
priority.

Apart form that, it works like a normal *Resource*:

.. code-block:: python

   >>> def resource_user(name, env, resource, wait, prio):
   ...     yield env.timeout(wait)
   ...     with resource.request(priority=prio) as req:
   ...         print('%s requesting at %s with priority=%s' % (name, env.now, prio))
   ...         yield req
   ...         print('%s got resource at %s' % (name, env.now))
   ...         yield env.timeout(3)
   ...
   >>> env = simpy.Environment()
   >>> res = simpy.PriorityResource(env, capacity=1)
   >>> p1 = env.process(resource_user(1, env, res, wait=0, prio=0))
   >>> p2 = env.process(resource_user(2, env, res, wait=1, prio=0))
   >>> p3 = env.process(resource_user(3, env, res, wait=2, prio=-1))
   >>> env.run()
   1 requesting at 0 with priority=0
   1 got resource at 0
   2 requesting at 1 with priority=0
   3 requesting at 2 with priority=-1
   3 got resource at 3
   2 got resource at 6

Although *p3* requested the resource later than *p2*, it could use it earlier
because its priority was higher.


PreemptiveResource
------------------

Sometimes, new requests are so important that queue-jumping is not enough and
they need to kick existing users out of the resource (this is called
*preemption*). The *PreemptiveResource* allows you to do exactly this:

.. code-block:: python

   >>> def resource_user(name, env, resource, wait, prio):
   ...     yield env.timeout(wait)
   ...     with resource.request(priority=prio) as req:
   ...         print('%s requesting at %s with priority=%s' % (name, env.now, prio))
   ...         yield req
   ...         print('%s got resource at %s' % (name, env.now))
   ...         try:
   ...             yield env.timeout(3)
   ...         except simpy.Interrupt as interrupt:
   ...             by = interrupt.cause.by
   ...             usage = env.now - interrupt.cause.usage_since
   ...             print('%s got preempted by %s at %s after %s' %
   ...                   (name, by, env.now, usage))
   ...
   >>> env = simpy.Environment()
   >>> res = simpy.PreemptiveResource(env, capacity=1)
   >>> p1 = env.process(resource_user(1, env, res, wait=0, prio=0))
   >>> p2 = env.process(resource_user(2, env, res, wait=1, prio=0))
   >>> p3 = env.process(resource_user(3, env, res, wait=2, prio=-1))
   >>> env.run()
   1 requesting at 0 with priority=0
   1 got resource at 0
   2 requesting at 1 with priority=0
   3 requesting at 2 with priority=-1
   1 got preempted by <Process(resource_user) object at 0x...> at 2 after 2
   3 got resource at 2
   2 got resource at 5

*PreemptiveResource* inherits from *PriorityResource* and adds a *preempt*
flag (that defaults to ``True``) to ``request()``. By setting this to ``False``
(``resource.request(priority=x, preempt=False)``), a process can decide to not
preempt another resource user. It will still be put in the queue according to
its priority, though.

The implementation of *PreemptiveResource* values priorities higher than
preemption. That means preempt request are not allowed to cheat and jump over
a higher prioritized request. The following example shows that preemptive low
priority requests cannot queue-jump over high priority requests:

.. code-block:: python

   >>> def user(name, env, res, prio, preempt):
   ...     with res.request(priority=prio, preempt=preempt) as req:
   ...         try:
   ...             print('%s requesting at %d' % (name, env.now))
   ...             yield req
   ...             print('%s got resource at %d' % (name, env.now))
   ...             yield env.timeout(3)
   ...         except simpy.Interrupt:
   ...             print('%s got preempted at %d' % (name, env.now))
   >>>
   >>> env = simpy.Environment()
   >>> res = simpy.PreemptiveResource(env, capacity=1)
   >>> A = env.process(user('A', env, res, prio=0, preempt=True))
   >>> env.run(until=1)  # Give A a head start
   A requesting at 0
   A got resource at 0
   >>> B = env.process(user('B', env, res, prio=-2, preempt=False))
   >>> C = env.process(user('C', env, res, prio=-1, preempt=True))
   >>> env.run()
   B requesting at 1
   C requesting at 1
   B got resource at 3
   C got resource at 6


1. Process *A* requests the resource with priority 0. It immediately becomes
   a user.

2. Process *B* requests the resource with priority -2 but sets *preempt* to
   ``False``. It will queue up and wait.

3. Process *C* requests the resource with priority -1 but leaves *preempt*
   ``True``. Normally, it would preempt *A* but in this case, *B* is queued up
   before *C* and prevents *C* from preempting *A*. *C* can also not preempt
   *B* since its priority is not high enough.

Thus, the behavior in the example is the same as if no preemption was used at
all. Be careful when using mixed preemption!

Due to the higher priority of process *B*, no preemption occurs in this
example. Note that an additional request with a priority of -3 would be able
to preempt *A*.

If your use-case requires a different behaviour, for example queue-jumping or
valuing preemption over priorities, you can subclass *PreemptiveResource* and
override the default behaviour.


.. _res_type_container:

Containers
==========

.. currentmodule:: simpy.resources.container

Containers help you modelling the production and consumption of a homogeneous,
undifferentiated bulk. It may either be continuous (like water) or discrete
(like apples).

You can use this, for example, to model the gas / petrol tank of a gas station.
Tankers increase the amount of gasoline in the tank while cars decrease it.

The following example is a very simple model of a gas station with a limited
number of fuel dispensers (modeled as ``Resource``) and a tank modeled as
``Container``:

.. code-block:: python

   >>> class GasStation:
   ...     def __init__(self, env):
   ...         self.fuel_dispensers = simpy.Resource(env, capacity=2)
   ...         self.gas_tank = simpy.Container(env, init=100, capacity=1000)
   ...         self.mon_proc = env.process(self.monitor_tank(env))
   ...
   ...     def monitor_tank(self, env):
   ...         while True:
   ...             if self.gas_tank.level < 100:
   ...                 print('Calling tanker at %s' % env.now)
   ...                 env.process(tanker(env, self))
   ...             yield env.timeout(15)
   >>>
   >>>
   >>> def tanker(env, gas_station):
   ...     yield env.timeout(10)  # Need 10 Minutes to arrive
   ...     print('Tanker arriving at %s' % env.now)
   ...     amount = gas_station.gas_tank.capacity - gas_station.gas_tank.level
   ...     yield gas_station.gas_tank.put(amount)
   >>>
   >>>
   >>> def car(name, env, gas_station):
   ...     print('Car %s arriving at %s' % (name, env.now))
   ...     with gas_station.fuel_dispensers.request() as req:
   ...         yield req
   ...         print('Car %s starts refueling at %s' % (name, env.now))
   ...         yield gas_station.gas_tank.get(40)
   ...         yield env.timeout(5)
   ...         print('Car %s done refueling at %s' % (name, env.now))
   >>>
   >>>
   >>> def car_generator(env, gas_station):
   ...     for i in range(4):
   ...         env.process(car(i, env, gas_station))
   ...         yield env.timeout(5)
   >>>
   >>>
   >>> env = simpy.Environment()
   >>> gas_station = GasStation(env)
   >>> car_gen = env.process(car_generator(env, gas_station))
   >>> env.run(35)
   Car 0 arriving at 0
   Car 0 starts refueling at 0
   Car 1 arriving at 5
   Car 0 done refueling at 5
   Car 1 starts refueling at 5
   Car 2 arriving at 10
   Car 1 done refueling at 10
   Car 2 starts refueling at 10
   Calling tanker at 15
   Car 3 arriving at 15
   Car 3 starts refueling at 15
   Tanker arriving at 25
   Car 2 done refueling at 30
   Car 3 done refueling at 30

Containers allow you to retrieve their current ``level`` as well as their
``capacity`` (see ``GasStation.monitor_tank()`` and ``tanker()``). You can also
access the list of waiting events via the ``put_queue`` and ``get_queue``
attributes (similar to ``Resource.queue``).

.. _res_type_store:

Stores
======

.. currentmodule:: simpy.resources.store

Using Stores you can model the production and consumption of concrete objects
(in contrast to the rather abstract "amount" stored in containers). A single
Store can even contain multiple types of objects.

Beside :class:`Store`, there is a :class:`FilterStore` that lets you use
a custom function to filter the objects you get out of the store.

Here is a simple example modelling a generic producer/consumer scenario:

.. code-block:: python

   >>> def producer(env, store):
   ...     for i in range(100):
   ...         yield env.timeout(2)
   ...         yield store.put('spam %s' % i)
   ...         print('Produced spam at', env.now)
   >>>
   >>>
   >>> def consumer(name, env, store):
   ...     while True:
   ...         yield env.timeout(1)
   ...         print(name, 'requesting spam at', env.now)
   ...         item = yield store.get()
   ...         print(name, 'got', item, 'at', env.now)
   >>>
   >>>
   >>> env = simpy.Environment()
   >>> store = simpy.Store(env, capacity=2)
   >>>
   >>> prod = env.process(producer(env, store))
   >>> consumers = [env.process(consumer(i, env, store)) for i in range(2)]
   >>>
   >>> env.run(until=5)
   0 requesting spam at 1
   1 requesting spam at 1
   Produced spam at 2
   0 got spam 0 at 2
   0 requesting spam at 3
   Produced spam at 4
   1 got spam 1 at 4

As with the other resource types, you can get a store's capacity via the
``capacity`` attribute. The attribute ``items`` points to the list of items
currently available in the store. The put and get queues can be accessed via
the ``put_queue`` and ``get_queue`` attributes.

*FilterStore* can, for example, be used to model machine shops where machines
have varying attributes. This can be useful if the homogeneous slots of
a *Resource* are not what you need:

.. code-block:: python

   >>> from collections import namedtuple
   >>>
   >>> Machine = namedtuple('Machine', 'size, duration')
   >>> m1 = Machine(1, 2)  # Small and slow
   >>> m2 = Machine(2, 1)  # Big and fast
   >>>
   >>> env = simpy.Environment()
   >>> machine_shop = simpy.FilterStore(env, capacity=2)
   >>> machine_shop.items = [m1, m2]  # Pre-populate the machine shop
   >>>
   >>> def user(name, env, ms, size):
   ...     machine = yield ms.get(lambda machine: machine.size == size)
   ...     print(name, 'got', machine, 'at', env.now)
   ...     yield env.timeout(machine.duration)
   ...     yield ms.put(machine)
   ...     print(name, 'released', machine, 'at', env.now)
   >>>
   >>>
   >>> users = [env.process(user(i, env, machine_shop, (i % 2) + 1))
   ...          for i in range(3)]
   >>> env.run()
   0 got Machine(size=1, duration=2) at 0
   1 got Machine(size=2, duration=1) at 0
   1 released Machine(size=2, duration=1) at 1
   0 released Machine(size=1, duration=2) at 2
   2 got Machine(size=1, duration=2) at 2
   2 released Machine(size=1, duration=2) at 4
