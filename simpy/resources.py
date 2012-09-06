"""
This modules contains Simpy's resource types:

- :class:`Resource`: Can be used by a limited number of processes at a
  time (e.g., a gas station with a limited number of fuel pumps).
- :class:`Container`: Models the production and consumption of a
  homogeneous, undifferentiated bulk. It may either be continuous (like
  water) or discrete (like apples).
- :class:`Store`: Allows the production and consumption of discrete
  Python objects.

  TODO: add more documentation.

"""
from simpy.queues import FIFO


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

    The ``sim`` parameter is the :class:`simpy.Simulation` instance the
    resource is bound to.

    The ``capacity`` defines the number of slots and must be a positive
    integer.

    The ``queue`` must provide a ``pop()`` method to get one item from
    it and a ``push(item)`` method to append an item. SimPy comes with
    a :class:`FIFO` (which is used as a default), :class:`LIFO` and
    a :class:`Priority` queue.

    You can get the list of users via the :attr:`users` attribute and
    the queue of waiting processes via :attr:`queue`. You should not
    change these, though.

    """
    def __init__(self, sim, capacity, queue=None):
        self._context = sim.context

        self.capacity = capacity
        """The resource's maximum capacity."""

        self.queue = queue if queue else FIFO()
        """The queue of waiting processes. Read only."""

        self.users = []
        """The list of the resource's users. Read only."""

    def request(self):
        """Request the resource.

        If the maximum capacity of users is not reached, the requesting
        process obtains the resource immediately (that is, a new event
        for it will be scheduled at the current time. That means that
        all other events also scheduled for the current time will be
        processed before that new event.).

        If the maximum capacity is reached, suspend the requesting
        process until another process releases the resource again.

        """
        proc = self._context.active_process
        if len(self.users) < self.capacity:
            self.users.append(proc)
            return self._context.hold(0)
        else:
            self.queue.push(proc)
            return self._context.suspend()

    def release(self):
        """Release the resource for the active process.

        Raise a :class:`ValueError` if the process did not request the
        resource in the first place.

        If another process is waiting for the resource, resume that
        process.

        """
        proc = self._context.active_process
        try:
            self.users.remove(proc)
        except ValueError:
            raise ValueError('Cannot release resource for %s since it was not '
                             'previously requested by it.' % proc)

        try:
            next_user = self.queue.pop()
        except IndexError:
            pass
        else:  # Only schedule event if someone was waiting ...
            self.users.append(next_user)
            self._context.resume(next_user)


class Container(object):
    """Models the production and consumption of a homogeneous,
    undifferentiated bulk. It may either be continuous (like water) or
    discrete (like apples).

    For example, a gasoline station stores gas (petrol) in large tanks.
    Tankers increase, and refuelled cars decrease, the amount of gas in
    the station's storage tanks.

    The ``sim`` parameter is the :class:`simpy.Simulation` instance the
    container is bound to.

    The ``capacity`` defines the size of the container and must be
    a positive number (> 0). By default, a container is of unlimited
    size.  You can specify the initial level of the container via
    ``init``. It must be >= 0 and is 0 by default. A :class:`ValueError`
    is raised if one of these values is negative.

    A container has two queues: ``put_q`` is used for processes that
    want to put something into the container, ``get_q`` is for those
    that want to get something out. The default for both is
    :class:`FIFO``.

    """
    def __init__(self, sim, capacity=None, init=0, put_q=None, get_q=None):
        self._context = sim.context

        if capacity <= 0:
            raise ValueError('capacity(=%s) must be > 0.' % capacity)
        if init < 0:
            raise ValueError('init(=%s) must be >= 0.' % init)

        self.capacity = capacity or Infinity
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
        """Put ``amount`` into the resource if possible or wait until it
        is.

        Raise a :class:`ValueError` if ``amount <= 0``.

        """
        if amount <= 0:
            raise ValueError('amount(=%s) must be > 0.' % amount)

        new_level = self._level + amount
        if new_level <= self.capacity:
            self._level = new_level
            # TODO: Get process from get_q if put would be successful.
            return self._context.hold(0)
        else:
            self.put_q.push(self._context.active_process)
            return self._context.suspend()

    def get(self, amount):
        """Get ``amount`` from the container if possible or wait until
        it is available.

        Raise a :class:`ValueError` if ``amount <= 0``.

        """
        if amount <= 0:
            raise ValueError('amount(=%s) must be > 0.' % amount)

        new_level = self._level - amount
        if new_level >= 0:
            self._level = new_level
            # TODO: Get process from put_q if put would be successful.
            return self._context.hold(0)
        else:
            self.get_q.push(self._context.active_process)
            return self.suspend()


class Store(object):
    """

    """
