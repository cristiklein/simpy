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


class Resource(object):
    """A resource has a limited number of slots that can be requested
    by a process.

    If all slots are taken, requesters are put into
    a queue. If a process releases a slot, the next process is popped
    from the queue and gets one slot.

    The *capacity* defines the number of slots and must be a positive
    integer.  The *queue* must provide a ``pop()`` method to get one
    item from it and a ``push(item)`` method to append an item. SimPy
    comes with a :class:`FIFO`, :class:`LIFO` and a :class:`Priority`
    queue.

    You can get the list of users via the :attr:`users` attribute and
    the queue of waiting processes via :attr:`queue`. You should not
    change these, though.

    """
    def __init__(self, context, capacity, queue=None):
        self._context = context

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
    """This is something where you add and remove items. If the level is
    empty, you can't remove any more items and are pushed to a quque ot
    wait for more items to be inserted. The same applies if you want to
    add items to the level.

    """

class Store(object):
    """

    """
