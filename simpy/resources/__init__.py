"""
This modules contains SimPy's resource types:

- :class:`Resource`: Can be used by a limited number of processes at a
  time (e.g., a gas station with a limited number of fuel pumps).
- :class:`PreemptiveResource`: Like :class:`Resource`, but with
  preemption.
- :class:`Container`: Models the production and consumption of a
  homogeneous, undifferentiated bulk. It may either be continuous (like
  water) or discrete (like apples).
- :class:`Store`: Allows the production and consumption of discrete
  Python objects.

"""
from simpy.resources import events, queues, util


Infinity = float('inf')


class Resource(object):
    """A resource has a limited number of slots that can be requested
    by a process.

    If all slots are taken, requesters are put into a queue. If
    a process releases a slot, the next process is popped from the queue
    and gets one slot.

    For example, a gas station has a limited number of fuel pumps
    that can be used by refueling vehicles. If all fuel pumps are
    occupied, incoming vehicles have to wait until one gets free.

    The ``env`` parameter is the :class:`~simpy.core.Environment`
    instance the resource is bound to.

    The ``capacity`` defines the number of slots and must be a positive
    integer.

    The resources uses :class:`~simpy.resources.events.ResourceEvent` as
    default ``event_type`` and :class:`~simpy.resources.util.Users` as
    default ``users_type``.

    """
    def __init__(self, env, capacity, event_type=events.ResourceEvent,
                 users_type=util.Users):
        self._env = env
        self._event = event_type
        self._users = users_type(capacity)
        self._queue = queues.SortedQueue()

    @property
    def count(self):
        """Number of users currently using the resource."""
        return len(self._users._users)

    @property
    def capacity(self):
        """Maximum caMacity of the resource."""
        return self._users._capacity

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
        event = self._event(self, proc, **kwargs)

        acquired = self._users.add(event)
        if not acquired:
            self._queue.push(event)

        return event

    def release(self, event):
        """Release the resource for the process that created event.

        If another process is waiting for the resource, resume that
        process.

        """
        try:
            self._users.remove(event)
        except ValueError:
            try:
                self._queue.remove(event)
            except ValueError:
                pass
        else:
            # Resume the next user if there is one
            if self._queue:
                event = self._queue.pop()
                self._users.add(event)

    def get_users(self):
        """Return a list with all processes using the resource."""
        return [event._proc for event in self._users._users]

    def get_queued(self):
        """Return a list with all queued processes."""
        return [event._proc for event in self._queue._items]


class PreemptiveResource(Resource):
    """This resource mostly works like :class:`Resource`, but users of
    the resource can be preempted by higher prioritized processes.

    The resources uses
    a :class:`simpy.resources.events.PriorityResourceEvent` as default
    ``event_type``. You need to pass a ``priority`` argument to
    :meth:`request()` that is then used to sort events and to decide
    whether a process gets preempted or not when another one requests
    the resource.

    """
    def __init__(self, env, capacity, event_type=events.PriorityResourceEvent):
        super(PreemptiveResource, self).__init__(env, capacity,
                event_type=event_type, users_type=util.PreemptiveUsers)


class BaseContainer(object):
    """Base class for all container types."""
    def __init__(self, env, capacity, event_type):
        if capacity <= 0:
            raise ValueError('capacity(=%s) must be > 0.' % capacity)

        self._env = env
        self._capacity = capacity
        self._event = event_type
        self._put_q = queues.SortedQueue()
        self._get_q = queues.SortedQueue()

    @property
    def capacity(self):
        """The maximum capactiy of the container."""
        return self._capacity

    def put(self):
        """Override this in your implementation to put sth. into the
        container."""
        raise NotImplementedError

    def get(self):
        """Override this in your implementation to take sth. out of the
        container."""
        raise NotImplementedError

    def release(self, event):
        """Cancel a put/get request to the queue.

        A process must call this when it was interrupt during a put/get
        request if the Container was not used as a context manager.

        """
        try:
            self._put_q.remove(event)
            self._get_q.remove(event)
        except ValueError:
            pass

    def get_put_queued(self):
        """Return a list with all processes in the *put queue*."""
        return self._get_queued(self._put_q)

    def get_get_queued(self):
        """Return a list with all processes in the *get queue*."""
        return self._get_queued(self._get_q)

    def _get_queued(self, queue):
        """Return a list with all processes in *queue*."""
        return [event._proc for event in queue._items]


class Container(BaseContainer):
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
    that want to get something out.

    The container uses a :class:`~simpy.resources.events.ContainerEvent`
    as default ``event_type``. That _event type sorts by creation time.
    Thus, the ``put_q`` and ``get_q`` behave like FIFO queues by
    default.

    """
    def __init__(self, env, capacity=Infinity, init=0,
                 event_type=events.ContainerEvent):
        if init < 0:
            raise ValueError('init(=%s) must be >= 0.' % init)
        super(Container, self).__init__(env, capacity, event_type)
        self._level = init

    @property
    def level(self):
        """The current level of the container (a number between ``0``
        and ``capacity``). Read only.

        """
        return self._level

    def put(self, amount):
        """Put ``amount`` into the Container if possible or wait until it is.

        Raise a :exc:`ValueError` if ``amount <= 0``.

        """
        if amount <= 0:
            raise ValueError('amount(=%s) must be > 0.' % amount)

        event = self._event(self, self._env.active_process, amount)
        new_level = self._level + amount

        # Process can put immediately
        if new_level <= self._capacity:
            self._level = new_level
            # Pop processes from the "get_q".
            while self._get_q:
                q_event = self._get_q.peek()
                if self._level >= q_event.amount:
                    self._get_q.pop()
                    self._level -= q_event.amount
                    q_event.succeed()
                else:
                    break
            event.succeed()

        # Process has to wait.
        else:
            self._put_q.push(event)

        return event

    def get(self, amount):
        """Get ``amount`` from the container if possible or wait until
        it is available.

        Raise a :exc:`ValueError` if ``amount <= 0``.

        """
        if amount <= 0:
            raise ValueError('amount(=%s) must be > 0.' % amount)

        event = self._event(self, self._env.active_process, amount)

        # Process can get immediately
        if self._level >= amount:
            self._level -= amount
            # Pop processes from the "put_q".
            while self._put_q:
                q_event = self._put_q.peek()
                new_level = self._level + q_event.amount
                if new_level <= self._capacity:
                    self._put_q.pop()
                    self._level = new_level
                    q_event.succeed()
                else:
                    break
            event.succeed()

        # Process has to wait.
        else:
            self._get_q.push(event)

        return event


class Store(BaseContainer):
    """Models the production and consumption of concrete Python objects.

    The type of items you can put into or get from the store is not
    defined. You can use normal Python objects, SimPy processes or
    other resources. You can even mix them as you want.

    The ``env`` parameter is the :class:`~simpy.core.Environment`
    instance the container is bound to.

    The ``capacity`` defines the size of the Store and must be
    a positive number (> 0). By default, a Store is of unlimited size.
    A :exc:`ValueError` is raised if the value is negative.

    A Store has three queues: ``put_q`` is used for processes that want
    to put something into the Store, ``get_q`` is for those that want to
    get something out. The ``item_q`` is used to store and retrieve the
    actual items. The default for the ``item_q_type`` is
    :class:`~simpy.resources.queues.FIFO`.

    The container uses a :class:`~simpy.resources.events.StoreEvent` as
    default ``event_type``. That event type sorts by creation time.
    Thus, the ``put_q`` and ``get_q`` behave like FIFO queues by
    default.

    """
    def __init__(self, env, capacity=Infinity, item_q_type=queues.FIFO,
                 event_type=events.StoreEvent):
        super(Store, self).__init__(env, capacity, event_type)
        self._item_q = item_q_type()

    @property
    def count(self):
        """The number of items in the Store (a number between ``0`` and
        ``capacity``). Read only.

        """
        return len(self._item_q)

    def put(self, item):
        """Put ``item`` into the Store if possible or wait until it is."""
        event = self._event(self, self._env.active_process, item)

        # Process can put immediately
        if len(self._item_q) < self._capacity:
            self._item_q.push(item)
            # Pop processes from the "get_q".
            while self._get_q and self._item_q:
                q_event = self._get_q.pop()
                get_item = self._item_q.pop()
                q_event.succeed(get_item)
            event.succeed()

        # Process has to wait.
        else:
            self._put_q.push(event)

        return event

    def get(self):
        """Get an item from the Store or wait until one is available."""
        event = self._event(self, self._env.active_process)

        # Process can get immediately
        if len(self._item_q):
            item = self._item_q.pop()
            # Pop processes from the "put_q"
            while self._put_q and (len(self._item_q) < self._capacity):
                q_event = self._put_q.pop()
                self._item_q.push(q_event.item)
                q_event.succeed()
            event.succeed(item)

        # Process has to wait
        else:
            self._get_q.push(event)

        return event
