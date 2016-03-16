==========
Monitoring
==========

Monitoring is a relatively complex topic with a lot of different use-cases and
lots of variations.

This guide presents some of the more common and more interesting ones.  It’s
purpose is to give you some hints and ideas how you can implement simulation
monitoring tailored to your use-cases.

So, before you start, you need to define them:


*What* do you want to monitor?

- :ref:`Your processes <monitoring-your-processes>`?

- :ref:`Resource usage <resource-usage>`?

- :ref:`Trace all events of the simulation <event-tracing>`?


*When* do you want to monitor?

- Regularly in defined intervals?

- When something happens?


*How* do you want to store the collected data?

 - Store it in a simple list?

 - Log it to a file?

 - Write it to a database?

 The following sections discuss these questions and provide some example code
 to help you.


.. _monitoring-your-processes:

Monitoring your processes
-------------------------

Monitoring your own processes is relatively easy, because *you* control the
code.  From our experience, the most common thing you might want to do is
monitor the value of one or more state variables every time they change or at
discrete intervals and store it somewhere (in memory, in a database, or in
a file, for example).

In the simples case, you just use a list and append the required value(s) every
time they change:

.. code-block:: python

   >>> import simpy
   >>>
   >>> data = []  # This list will hold all collected data
   >>>
   >>> def test_process(env, data):
   ...     val = 0
   ...     for i in range(5):
   ...         val += env.now
   ...         data.append(val)  # Collect data
   ...         yield env.timeout(1)
   >>>
   >>> env = simpy.Environment()
   >>> p = env.process(test_process(env, data))
   >>> env.run(p)
   >>> print('Collected', data)  # Lets see what we got
   Collected [0, 1, 3, 6, 10]

If you want to monitor multiple variables, you can append (named)tuples to your
data list.

If you want to store the data in a NumPy array or a database, you can often
increase performance if you buffer the data in a plain Python list and only
write larger chunks (or the complete dataset) to the database.


.. _resource-usage:

Resource usage
--------------

The use-cases for resource monitoring are numerous, for example you might want
to monitor:

- Utilization of a resource over time and on average, that is,

  - the number of processes that are using the resource at a time

  - the level of a container

  - the amount of items in a store

  This can be monitored either in discrete time steps or every time there is
  a change.

- Number of processes in the (put|get)queue over time (and the average).
  Again, this could be monitored at discrete time steps or every time there is
  a change.

- For *PreemptiveResource*, you may want to measure how often preemption occurs
  over time.

In contrast to your processes, you don't have direct access to the code of the
built-in resource classes.  But this doesn't prevent you from monitoring them.

Monkey-patching some of a resource's methods allows you to gather all the data
you need.

Here is an example that demonstrate how you can add callbacks to
a resource that get called just before or after a *get / request* or a *put
/ release* event:

.. code-block:: python

   >>> from functools import partial, wraps
   >>> import simpy
   >>>
   >>> def patch_resource(resource, pre=None, post=None):
   ...     """Patch *resource* so that it calls the callable *pre* before each
   ...     put/get/request/release operation and the callable *post* after each
   ...     operation.  The only argument to these functions is the resource
   ...     instance.
   ...
   ...     """
   ...     def get_wrapper(func):
   ...         # Generate a wrapper for put/get/request/release
   ...         @wraps(func)
   ...         def wrapper(*args, **kwargs):
   ...             # This is the actual wrapper
   ...             # Call "pre" callback
   ...             if pre:
   ...                 pre(resource)
   ...
   ...             # Perform actual operation
   ...             ret = func(*args, **kwargs)
   ...
   ...             # Call "post" callback
   ...             if post:
   ...                 post(resource)
   ...
   ...             return ret
   ...         return wrapper
   ...
   ...     # Replace the original operations with our wrapper
   ...     for name in ['put', 'get', 'request', 'release']:
   ...         if hasattr(resource, name):
   ...             setattr(resource, name, get_wrapper(getattr(resource, name)))
   >>>
   >>> def monitor(data, resource):
   ...     """This is our monitoring callback."""
   ...     item = (
   ...         resource._env.now,  # The current simulation time
   ...         resource.count,  # The number of users
   ...         len(resource.queue),  # The number of queued processes
   ...     )
   ...     data.append(item)
   >>>
   >>> def test_process(env, res):
   ...     with res.request() as req:
   ...         yield req
   ...         yield env.timeout(1)
   >>>
   >>> env = simpy.Environment()
   >>>
   >>> res = simpy.Resource(env, capacity=1)
   >>> data = []
   >>> # Bind *data* as first argument to monitor()
   >>> # see https://docs.python.org/3/library/functools.html#functools.partial
   >>> monitor = partial(monitor, data)
   >>> patch_resource(res, post=monitor)  # Patches (only) this resource instance
   >>>
   >>> p = env.process(test_process(env, res))
   >>> env.run(p)
   >>>
   >>> print(data)
   [(0, 1, 0), (1, 0, 0)]

The example above is a very generic but also very flexible way to monitor all
aspects of all kinds of resources.

The other extreme would be to fit the monitoring to exactly one use case.
Imagine, for example, you only want to know how many processes are waiting for
a ``Resource`` at a time:

.. code-block:: python

   >>> import simpy
   >>>
   >>> class MonitoredResource(simpy.Resource):
   ...     def __init__(self, *args, **kwargs):
   ...         super().__init__(*args, **kwargs)
   ...         self.data = []
   ...
   ...     def request(self, *args, **kwargs):
   ...         self.data.append((self._env.now, len(self.queue)))
   ...         return super().request(*args, **kwargs)
   ...
   ...     def release(self, *args, **kwargs):
   ...         self.data.append((self._env.now, len(self.queue)))
   ...         return super().release(*args, **kwargs)
   >>>
   >>> def test_process(env, res):
   ...     with res.request() as req:
   ...         yield req
   ...         yield env.timeout(1)
   >>>
   >>> env = simpy.Environment()
   >>>
   >>> res = MonitoredResource(env, capacity=1)
   >>> p1 = env.process(test_process(env, res))
   >>> p2 = env.process(test_process(env, res))
   >>> env.run()
   >>>
   >>> print(res.data)
   [(0, 0), (0, 0), (1, 1), (2, 0)]

In contrast to the first example, we now haven't patched a single resource
instance but the whole class.  It also removed all of the first example's
flexibility: We only monitor ``Resource`` typed resources, we only collect data
*before* the actual requests are made and we only collect the time and queue
length.  At the same time, you need less than half of the code.


.. _event-tracing:

Event tracing
-------------

.. currentmodule:: simpy.core

In order to debug or visualize a simulation, you might want to trace when
events are created, triggered and processed.  Maybe you also want to trace
which process created an event and which processes waited for an event.

The two most interesting functions for these use-cases are
:meth:`Environment.step()`, where all events get processed, and
:meth:`Environment.schedule()`, where all events get scheduled and inserted
into SimPy's event queue.

Here is an example that shows how :meth:`Environment.step()` can be patched in
order to trace all processed events:

.. code-block:: python

   >>> from functools import partial, wraps
   >>> import simpy
   >>>
   >>> def trace(env, callback):
   ...     """Replace the ``step()`` method of *env* with a tracing function
   ...     that calls *callbacks* with an events time, priority, ID and its
   ...     instance just before it is processed.
   ...
   ...     """
   ...     def get_wrapper(env_step, callback):
   ...         """Generate the wrapper for env.step()."""
   ...         @wraps(env_step)
   ...         def tracing_step():
   ...             """Call *callback* for the next event if one exist before
   ...             calling ``env.step()``."""
   ...             if len(env._queue):
   ...                 t, prio, eid, event = env._queue[0]
   ...                 callback(t, prio, eid, event)
   ...             return env_step()
   ...         return tracing_step
   ...
   ...     env.step = get_wrapper(env.step, callback)
   >>>
   >>> def monitor(data, t, prio, eid, event):
   ...     data.append((t, eid, type(event)))
   >>>
   >>> def test_process(env):
   ...     yield env.timeout(1)
   >>>
   >>> data = []
   >>> # Bind *data* as first argument to monitor()
   >>> # see https://docs.python.org/3/library/functools.html#functools.partial
   >>> monitor = partial(monitor, data)
   >>>
   >>> env = simpy.Environment()
   >>> trace(env, monitor)
   >>>
   >>> p = env.process(test_process(env))
   >>> env.run(until=p)
   >>>
   >>> for d in data:
   ...     print(d)
   (0, 0, <class 'simpy.events.Initialize'>)
   (1, 1, <class 'simpy.events.Timeout'>)
   (1, 2, <class 'simpy.events.Process'>)

The example above is inspired by a pull request from Steve Pothier.

Using the same concepts, you can also patch :meth:`Environment.schedule()`.
This would give you central access to the information when which event is
scheduled for what time.

In addition to that, you could also patch some or all of SimPy's event classes,
e.g., their `__init__()` method in order to trace when and how an event is
initially being created.
