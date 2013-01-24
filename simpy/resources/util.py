"""
Utility classes for the resources.

- :class:`Preempted`: Used as interrupt cause for preempted processes.

- :class:`Users`: Default user manager used by
  :class:`~simpy.resources.Resource`.

- :class:`PreemptiveUsers`: User manager used by
  :class:`~simpy.resources.PreemptiveResource`.

"""
from collections import namedtuple


Preempted = namedtuple('Preempted', 'by, usage_since')
"""Used as interrupt cause for preempted processes."""


class Users(object):
    """Default user queue implementation used by
    :class:`~simpy.resources.Resource`.

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


class PreemptiveUsers(Users):
    """Inherits :class:`Users` and adds preemption to it.

    If no slot is available for a new user, it checks if it can preempt
    another user.

    """
    def add(self, event):
        """Try to add ``event`` to the user queue. If this fails, try to
        preempt another user.

        The preemption is done by comparing the
        :attr:`simpy.resources.events.ResourceEvent.key` attributes of
        all users. If one of them is greater than the key of ``event``,
        it will be preempted and an :class:`~simpy.core.Interrupt` is
        thrown into the corresponding process.

        Return ``True`` if ``event`` could be added to the users (either
        normally or by preemption), ``False`` if not.

        """
        acquired = super(PreemptiveUsers, self).add(event)
        if acquired:
            return True

        # Check if we want to preempt
        if not event.preempt:
            return False

        # Check if we can preempt another process
        preempt = sorted(self._users, key=lambda e: e.key)[-1]

        if preempt.key > event.key:
            self._users.remove(preempt)
            preempt._proc.interrupt(Preempted(by=event._proc,
                                              usage_since=preempt.time))
            acquired = super(PreemptiveUsers, self).add(event)
            if not acquired:
                raise RuntimeError('Preemption failed.')
            return True

        return False
