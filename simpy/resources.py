"""
This modules contains simpy's resource types:

- :class:`Resource`: Can be used by a limited number of processes at a
  time (e.g., a gas station with a limited number of fuel pumps).
- :class:`PreemptiveResource`: Like :class:`Resource`, but with
  preemption.
- :class:`Container`: Models the production and consumption of a
  homogeneous, undifferentiated bulk. It may either be continuous (like
  water) or discrete (like apples).
- :class:`Store`: Allows the production and consumption of discrete
  Python objects.
- :class:`ResourceEvent`: Event type used by :class:`Resource`.

"""
from collections import namedtuple

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
    def __init__(self, resource, proc, kwargs, key):
        env = resource._env
        super(ResourceEvent, self).__init__(env)

        self._resource = resource
        self._proc = proc

        self.time = env.now
        """Time that this event was created on."""

        self.kwargs = kwargs
        """``**kwargs`` that were passed to :meth:`Resource.request()`."""

        self.key = key(self)
        """Value that is used for sorting resource events."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        self.release()

    def release(self):
        """Release the resource for this event.

        If another process is waiting for the resource, resume that
        process.

        """
        users = self._resource.users
        queue = self._resource.queue
        try:
            users.remove(self)
        except ValueError:
            try:
                queue.remove(self)
            except ValueError:
                pass
        else:
            # Resume the next user if there is one
            if queue:
                event = queue.pop()
                users.add(event)


class UserQueue(object):
    """Default user queue implementation used by :class:`Resource`.

    Upon request, it adds a user if a slot is available and does nothing
    if not.

    """
    def __init__(self, capacity):
        self._capacity = capacity
        self._users = []

    def add(self, event):
        """Add ``event`` to the user queue if a slot is available.

        Return ``True`` if the event could be added, ``False`` if not.

        """
        if len(self._users) < self._capacity:
            self._users.append(event)
            event.succeed()
            return True

        return False

    def remove(self, event):
        """Remove ``event`` from the users queue.

        Raise a :exc:`ValueError` if the event is not in the queue.

        """
        self._users.remove(event)


class PreemptiveUserQueue(UserQueue):
    """Inherits :class:`UserQueue` and adds preemption to it.

    If no slot is available for a new user, it checks if it can preempt
    another user.

    """
    def add(self, event):
        """Try to add ``event`` to the user queue. If this fails, try to
        preempt another user.

        The preemption is done by comparing the
        :attr:`~ResourceEvent.key` attributes of all users. If one of
        them is greater than the key of ``event``, it will be preempted
        and an :class:`~simpy.core.Interrupt` is thrown into the
        corresponding process.

        Return ``True`` if ``event`` could be added to the users (either
        normally or by preemption), ``False`` if not.

        """
        acquired = super(PreemptiveUserQueue, self).add(event)
        if acquired:
            return True

        # Check if we can preempt another process
        preempt = sorted(self._users, key=lambda evt: evt.key)[-1]

        if preempt.key > event.key:
            self._users.remove(preempt)
            preempt._proc.interrupt(Preempted(by=event._proc,
                                              usage_since=preempt.time))
            acquired = super(PreemptiveUserQueue, self).add(event)
            if not acquired:
                raise RuntimeError('Preemption failed.')
            return True

        return False


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

    ``user_queue`` defines the user queue to use. A user queue
    implements how and if a process can acquire the resource. The
    default user queue (:class:`UserQueue`) only adds a user if a slot
    is free and causes it to be pushed to the waiters queue if not. The
    :class:`PreemptiveUserQueue` on the other side may preempt another
    user if its priority is lower than that of the requesting user.

    You can specify the way users (or :class:`ResourceEvent`, to be
    precise) are compared by passing a ``key`` function that extracts
    the comparison key from the :class:`ResourceEvent` (see
    :func:`sorted()` for more details). `Smaller` events are favored by
    the :class:`~simpy.queues.Priority` queue and are less likely to be
    preempted.

    Note, that the ``key`` function is not used by all queues and users
    queues. Built-in classes that use it: :class:`PreemptiveUserQueue`,
    :class:`~simpy.queues.Priority`. By default, events are sorted by
    the time that they requested the resource (``key=lambda event:
    event.time``).

    """
    def __init__(self, env, capacity, queue=None, user_queue=None, key=None):
        self._env = env

        self.queue = FIFO() if queue is None else queue
        """The queue of waiting processes. Read only."""

        self.users = user_queue if user_queue else UserQueue(capacity)
        """The list of the resource's users. Read only."""

        self.key = key if key else lambda evt: evt.time
        """Function that can be used for ``key`` in :func:`sorted()`."""

    @property
    def count(self):
        """Number of users currently using the resource."""
        return len(self.users._users)

    @property
    def capacity(self):
        """Maximum capacity of the resource."""
        return self.users._capacity

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
        event = ResourceEvent(self, proc, kwargs, self.key)

        acquired = self.users.add(event)
        if not acquired:
            self.queue.push(event)

        return event


class PreemptiveResource(Resource):
    """This resource mostly works like :class:`Resource`, but users of
    the resource can be preempted by higher prioritized processes.

    The resources uses a :class:`simpy.queues.Priority` queue and the
    :class:`PreemptiveUserQueue` by default. The default ``key``
    function sorts by the ``priority`` keyword (that has to be passed to
    every :meth:`Resource.request()` call and the time of the request:
    ``key=lambda event: (event.kwargs['prioriy'], evt.time)`` (A lower
    number means a higher priority!))

    See :meth:`Resource.request()` for more information.

    """
    def __init__(self, env, capacity, queue=None, key=None):
        queue = Priority() if queue is None else queue
        users = PreemptiveUserQueue(capacity)
        key = lambda evt: (evt.kwargs['priority'], evt.time)
        super(PreemptiveResource, self).__init__(env, capacity, queue, users,
                                                 key)


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
