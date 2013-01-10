"""
This modules contains simpy's resource types:

- :class:`ResourceEvent`: Event type used by :class:`Resource`.
- :class:`Resource`: Can be used by a limited number of processes at a
  time (e.g., a gas station with a limited number of fuel pumps).
- :class:`PreemptiveResource`: Like :class:`Resource`, but with
  preemption.
- :class:`Container`: Models the production and consumption of a
  homogeneous, undifferentiated bulk. It may either be continuous (like
  water) or discrete (like apples).
- :class:`Store`: Allows the production and consumption of discrete
  Python objects.

  TODO: add more documentation.

"""
from collections import namedtuple
from itertools import count

from simpy.core import Event
from simpy.queues import FIFO, Priority


Infinity = float('inf')
Preempted = namedtuple('Preempted', 'by, usage_since')


class ResourceEvent(Event):
    """A normal :class:`~simpy.core.Event` that can be used as a
    context manager.

    A *ResourceEvent* is returned by :meth:`Resource.request()`:

    .. code-block:: python

        with resource.request() as request:
            yield request

    """
    def __init__(self, env, resource, proc, data):
        super(ResourceEvent, self).__init__(env)
        self._resource = resource

        # These attributes are used by the resource implementations.
        self.proc = proc
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        self._resource.release()


class Resource(object):
    """A resource has a limited number of slots that can be requested
    by a process.

    If all slots are taken, requesters are put into
    a queue. If a process releases a slot, the next process is popped
    from the queue and gets one slot.

    For example, a gas station has a limited number of fuel pumps
    that can be used by refueling vehicles. If all fuel pumps are
    occupied, incoming vehicles have to wait until one gets free.

    The ``env`` parameter is the :class:`~simpy.core.Environment`
    instance the resource is bound to.

    The ``capacity`` defines the number of slots and must be a positive
    integer.

    The ``queue`` must provide a ``pop()`` method to get one item from
    it and a ``push(item)`` method to append an item. simpy comes with
    a :class:`~simpy.queues.FIFO` (which is used as a default),
    :class:`~simpy.queues.LIFO` and a :class:`~simpy.queues.Priority`
    queue.

    You can get the list of users via the :attr:`users` attribute and
    the queue of waiting processes via :attr:`queue`. You should not
    change these, though.

    """
    def __init__(self, env, capacity, queue=None):
        self._env = env

        self.capacity = capacity
        """The resource's maximum capacity."""

        self.queue = FIFO() if queue is None else queue
        """The queue of waiting processes. Read only."""

        self.users = {}
        """The list of the resource's users. Read only."""

    def request(self, **kwargs):
        """Request the resource.

        If the maximum capacity of users is not reached, the requesting
        process obtains the resource immediately (that is, a new event
        for it will be scheduled at the current time. That means that
        all other events also scheduled for the current time will be
        processed before that new event.).

        If the maximum capacity is reached, suspend the requesting
        process until another process releases the resource again.

        """
        proc = self._env.active_process
        event = ResourceEvent(self._env, self, proc, self._get_data(kwargs))

        if len(self.users) < self.capacity:
            self._acquire_resource(event, **kwargs)
        else:
            self._resource_occupied(event, kwargs)

        return event

    def release(self):
        """Release the resource for the active process.

        If another process is waiting for the resource, resume that
        process.

        """
        proc = self._env.active_process
        try:
            del self.users[proc]
        except KeyError:
            # Check if the process is still waiting and remove it (this
            # happens if the process is interrupted while waiting).
            for i, evt in enumerate(self.queue):
                if evt.proc is proc:
                    del self.queue[i]
                    break

        # Resume the next user if there is one
        if self.queue and (len(self.users) < self.capacity):
            event = self.queue.pop()
            self._acquire_resource(event)

    def _acquire_resource(self, event, **kwargs):
        self.users[event.proc] = event.data
        event.succeed()

    def _get_data(self, kwargs):
        return None

    def _resource_occupied(self, event, kwargs):
        self.queue.push(event, **kwargs)


class PreemptiveResource(Resource):
    """This resource mostly works like :class:`Resource`, but users of
    the resource can be preempted by higher prioritized processes.

    The resources uses a :class:`simpy.queues.Priority` queue by
    default. If you pass a custom ``queue`` instance, its ``push()``
    method needs to take a ``priority`` argument.

    See :meth:`request()` for more information.

    """
    def __init__(self, env, capacity, queue=None):
        queue = Priority() if queue is None else queue
        super(PreemptiveResource, self).__init__(env, capacity, queue)
        self._user_counter = count()

    def request(self, priority, **kwargs):
        """Request the resource.

        If the maximum capacity of users is not reached, the requesting
        process obtains the resource immediately (that is, a new event
        for it will be scheduled at the current time. That means that
        all other events also scheduled for the current time will be
        processed before that new event.).

        If the maximum capacity is reached, check if some users of the
        resource have a lower priority as the requesting process.
        Preempt the user with the lowest priorities of them. If multiple
        users have the same priority, preempt the longest user.

        If no users has a lower priority, queue the requesting process.

        """
        kwargs.update(priority=priority)
        return super(PreemptiveResource, self).request(**kwargs)

    def _get_data(self, kwargs):
        return (
            kwargs['priority'],
            self._env.now,
            next(self._user_counter),
        )

    def _resource_occupied(self, event, kwargs):
        # Check if we can preempt another process
        users = (u_data + (u_proc,) for u_proc, u_data in self.users.items())
        p_prio, p_time, p_userid, p_proc = sorted(users)[0]
        # NOTE: Allow users to pass a custom "key" function to "sorted()"?

        priority = kwargs['priority']
        proc = event.proc
        if p_prio < priority:
            # Preempt it
            del self.users[p_proc]
            p_proc.interrupt(Preempted(by=proc, usage_since=p_time))
            self._acquire_resource(event, **kwargs)
        else:
            # No preemption possible
            self.queue.push(event, **kwargs)


class Container(object):
    """Models the production and consumption of a homogeneous,
    undifferentiated bulk. It may either be continuous (like water) or
    discrete (like apples).

    For example, a gasoline station stores gas (petrol) in large tanks.
    Tankers increase, and refuelled cars decrease, the amount of gas in
    the station's storage tanks.

    The ``env`` parameter is the :class:`~simpy.core.Environment`
    instance the container is bound to.

    The ``capacity`` defines the size of the container and must be
    a positive number (> 0). By default, a container is of unlimited
    size.  You can specify the initial level of the container via
    ``init``. It must be >= 0 and is 0 by default. A :exc:`ValueError`
    is raised if one of these values is negative.

    A container has two queues: ``put_q`` is used for processes that
    want to put something into the container, ``get_q`` is for those
    that want to get something out. The default for both is
    :class:`~simpy.queues.FIFO`.

    """
    def __init__(self, env, capacity=Infinity, init=0, put_q=None, get_q=None):
        self._env = env

        if capacity <= 0:
            raise ValueError('capacity(=%s) must be > 0.' % capacity)
        if init < 0:
            raise ValueError('init(=%s) must be >= 0.' % init)

        self.capacity = capacity
        """The maximum capacity of the container. You should not change
        its value."""
        self._level = init

        self.put_q = put_q or FIFO()
        """The queue for processes that want to put something in. Read only."""
        self.get_q = get_q or FIFO()
        """The queue for processes that want to get something out. Read only.
        """

    @property
    def level(self):
        """The current level of the container (a number between ``0``
        and ``capacity``). Read only.

        """
        return self._level

    def put(self, amount):
        """Put ``amount`` into the Container if possible or wait until
        it is.

        Raise a :exc:`ValueError` if ``amount <= 0``.

        """
        if amount <= 0:
            raise ValueError('amount(=%s) must be > 0.' % amount)

        new_level = self._level + amount
        new_event = self._env.event()

        # Process can put immediately
        if new_level <= self.capacity:
            self._level = new_level

            # Pop processes from the "get_q".
            while self.get_q:
                event, proc, amount = self.get_q.peek()

                # Try to find another process if proc is no longer waiting.
                if proc.target is not event:
                    self.get_q.pop()
                    continue

                if self._level >= amount:
                    self.get_q.pop()
                    self._level -= amount
                    event.succeed()
                else:
                    break

            new_event.succeed()

        # Process has to wait.
        else:
            self.put_q.push((new_event, self._env.active_process, amount))

        return new_event

    def get(self, amount):
        """Get ``amount`` from the container if possible or wait until
        it is available.

        Raise a :exc:`ValueError` if ``amount <= 0``.

        """
        if amount <= 0:
            raise ValueError('amount(=%s) must be > 0.' % amount)

        new_event = self._env.event()

        # Process can get immediately
        if self._level >= amount:
            self._level -= amount

            # Pop processes from the "put_q".
            while self.put_q:
                event, proc, amout = self.put_q.peek()

                # Try to find another process if proc is no longer waiting.
                if proc.target is not event:
                    self.get_q.pop()
                    continue

                new_level = self._level + amount
                if new_level <= self.capacity:
                    self.put_q.pop()
                    self._level = new_level
                    event.succeed()
                else:
                    break

            new_event.succeed()

        # Process has to wait.
        else:
            self.get_q.push((new_event, self._env.active_process, amount))

        return new_event


class Store(object):
    """Models the production and consumption of concrete Python objects.

    The type of items you can put into or get from the store is not
    defined. You can use normal Python objects, SimPy processes or
    other resources. You can even mix them as you want.

    The ``env`` parameter is the :class:`~simpy.core.Environment`
    instance the container is bound to.

    The ``capacity`` defines the size of the Store and must be
    a positive number (> 0). By default, a Store is of unlimited size.
    A :exc:`ValueError` is raised if the value is negative.

    A container has three queues: ``put_q`` is used for processes that
    want to put something into the Store, ``get_q`` is for those that
    want to get something out. The ``item_q`` is used to store and
    retrieve the actual items. The default for all of them is
    :class:`~simpy.queues.FIFO`.

    """
    def __init__(self, env, capacity=Infinity, put_q=None, get_q=None,
                 item_q=None):
        self._env = env

        if capacity <= 0:
            raise ValueError('capacity(=%s) must be > 0.' % capacity)

        self.capacity = capacity
        """The maximum capacity of the Store. You should not change its
        value."""

        self.put_q = put_q or FIFO()
        """The queue for processes that want to put something in. Read only."""
        self.get_q = get_q or FIFO()
        """The queue for processes that want to get something out. Read only.
        """
        self.item_q = item_q or FIFO()
        """The queue that stores the items of the store. Read only."""

    @property
    def count(self):
        """The number of items in the Store (a number between ``0`` and
        ``capacity``). Read only.

        """
        return len(self.item_q)

    def put(self, item):
        """Put ``item`` into the Store if possible or wait until it is."""
        new_event = self._env.event()

        # Process can put immediately
        if len(self.item_q) < self.capacity:
            self.item_q.push(item)

            # Pop processes from the "get_q".
            while self.get_q and self.item_q:
                event, proc = self.get_q.pop()

                # Try to find another process if proc is no longer waiting.
                if proc.target is not event:
                    continue

                get_item = self.item_q.pop()
                event.succeed(get_item)

            new_event.succeed()

        # Process has to wait.
        else:
            self.put_q.push((new_event, self._env.active_process, item))

        return new_event

    def get(self):
        """Get an item from the Store or wait until one is available."""
        new_event = self._env.event()

        if len(self.item_q):
            item = self.item_q.pop()

            # Pop processes from the "push_q"
            while self.put_q and (len(self.item_q) < self.capacity):
                event, proc, put_item = self.put_q.pop()

                # Try to find another process if proc is no longer waiting.
                if proc._target is not event:
                    continue

                self.item_q.push(put_item)
                event.succeed()

            new_event.succeed(item)

        # Process has to wait
        else:
            self.get_q.push((new_event, self._env.active_process))

        return new_event
