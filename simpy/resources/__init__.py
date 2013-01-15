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

    The resources uses :class:`~simpy.resources.events.ResourceEvent` as
    default ``event_type`` and :class:`~simpy.resources.util.Users` as
    default ``users_type``.

    """
    def __init__(self, env, capacity, event_type=events.ResourceEvent,
                 users_type=util.Users):
        self._env = env

        self.event = event_type
        """The event type that the queue uses."""

        self.users = users_type(capacity)
        """The list of the resource's users. Read only."""

        self.queue = queues.SortedQueue()
        """The queue of waiting processes. Read only."""

    @property
    def count(self):
        """Number of users currently using the resource."""
        return len(self.users._users)

    @property
    def capacity(self):
        """Maximum caMacity of the resource."""
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
        event = self.event(self, proc, **kwargs)

        acquired = self.users.add(event)
        if not acquired:
            self.queue.push(event)

        return event

    def release(self, event):
        """Release the resource for the process that created event.

        If another process is waiting for the resource, resume that
        process.

        """
        try:
            self.users.remove(event)
        except ValueError:
            try:
                self.queue.remove(event)
            except ValueError:
                pass
        else:
            # Resume the next user if there is one
            if self.queue:
                event = self.queue.pop()
                self.users.add(event)


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
    that want to get something out.

    The container uses a :class:`~simpy.resources.events.ContainerEvent`
    as default ``event_type``. That event type sorts by creation time.
    Thus, the ``put_q`` and ``get_q`` behave like FIFO queues by
    default.

    """
    def __init__(self, env, capacity=Infinity, init=0,
                 event_type=events.ContainerEvent):
        if capacity <= 0:
            raise ValueError('capacity(=%s) must be > 0.' % capacity)
        if init < 0:
            raise ValueError('init(=%s) must be >= 0.' % init)

        self.event = event_type
        """The event type the container uses."""

        self.capacity = capacity
        """The maximum capacity of the container. You should not change
        its value."""

        self.put_q = queues.SortedQueue()
        """The queue for processes that want to put something in. Read only."""

        self.get_q = queues.SortedQueue()
        """The queue for processes that want to get something out. Read only.
        """

        self._env = env
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

        event = self.event(self, self._env.active_process, amount)
        new_level = self._level + amount

        # Process can put immediately
        if new_level <= self.capacity:
            self._level = new_level
            # Pop processes from the "get_q".
            while self.get_q:
                q_event = self.get_q.peek()
                if self._level >= q_event.amount:
                    self.get_q.pop()
                    self._level -= q_event.amount
                    q_event.succeed()
                else:
                    break
            event.succeed()

        # Process has to wait.
        else:
            self.put_q.push(event)

        return event

    def get(self, amount):
        """Get ``amount`` from the container if possible or wait until
        it is available.

        Raise a :exc:`ValueError` if ``amount <= 0``.

        """
        if amount <= 0:
            raise ValueError('amount(=%s) must be > 0.' % amount)

        event = self.event(self, self._env.active_process, amount)

        # Process can get immediately
        if self._level >= amount:
            self._level -= amount
            # Pop processes from the "put_q".
            while self.put_q:
                q_event = self.put_q.peek()
                new_level = self._level + q_event.amount
                if new_level <= self.capacity:
                    self.put_q.pop()
                    self._level = new_level
                    q_event.succeed()
                else:
                    break
            event.succeed()

        # Process has to wait.
        else:
            self.get_q.push(event)

        return event

    def release(self, event):
        """Cancel a put/get request to the queue.

        A process must call this when it was interrupt during a put/get
        request if the Container was not used as a context manager.

        """
        try:
            self.put_q.remove(event)
            self.get_q.remove(event)
        except ValueError:
            pass


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
    retrieve the actual items. The default for the ``item_q_type`` is
    :class:`~simpy.resources.queues.FIFO`.

    The container uses a :class:`~simpy.resources.events.StoreEvent`
    as default ``event_type``. That event type sorts by creation time.
    Thus, the ``put_q`` and ``get_q`` behave like FIFO queues by
    default.

    """
    def __init__(self, env, capacity=Infinity, item_q_type=queues.FIFO,
                 event_type=events.StoreEvent):
        if capacity <= 0:
            raise ValueError('capacity(=%s) must be > 0.' % capacity)

        self.event = event_type
        """The event type the container uses."""

        self.capacity = capacity
        """The maximum capacity of the Store. You should not change its
        value."""

        self.put_q = queues.SortedQueue()
        """The queue for processes that want to put something in. Read only."""

        self.get_q = queues.SortedQueue()
        """The queue for processes that want to get something out. Read only.
        """
        self.item_q = item_q_type()
        """The queue that stores the items of the store. Read only."""

        self._env = env

    @property
    def count(self):
        """The number of items in the Store (a number between ``0`` and
        ``capacity``). Read only.

        """
        return len(self.item_q)

    def put(self, item):
        """Put ``item`` into the Store if possible or wait until it is."""
        event = self.event(self, self._env.active_process, item)

        # Process can put immediately
        if len(self.item_q) < self.capacity:
            self.item_q.push(item)
            # Pop processes from the "get_q".
            while self.get_q and self.item_q:
                q_event = self.get_q.pop()
                get_item = self.item_q.pop()
                q_event.succeed(get_item)
            event.succeed()

        # Process has to wait.
        else:
            self.put_q.push(event)

        return event

    def get(self):
        """Get an item from the Store or wait until one is available."""
        event = self.event(self, self._env.active_process)

        # Process can get immediately
        if len(self.item_q):
            item = self.item_q.pop()
            # Pop processes from the "put_q"
            while self.put_q and (len(self.item_q) < self.capacity):
                q_event = self.put_q.pop()
                self.item_q.push(q_event.item)
                q_event.succeed()
            event.succeed(item)

        # Process has to wait
        else:
            self.get_q.push(event)

        return event

    def release(self, event):
        """Cancel a put/get request to the queue.

        A process must call this when it was interrupt during a put/get
        request if the Store was not used as a context manager.

        """
        try:
            self.put_q.remove(event)
            self.get_q.remove(event)
        except ValueError:
            pass
