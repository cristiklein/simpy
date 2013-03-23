"""
This modules contains some queues that can be used with SimPy's
resources, namely a :class:`FIFO` and a :class:`LIFO` queue as well as a
:class:`SortedQueue` queue.
"""
from collections import deque


class Queue(object):
    """Interface for resource queues, which is a subset of Python's default
    ``list`` interface. Resources do not check the type of their
    queues what allows to simply use ``list`` or ``deque`` as a queue.
    """

    def append(self, event):
        """Appends the ``event`` to this queue."""
        raise NotImplementedError(self)

    def remove(self, event):
        """Removes the ``event`` from this queue."""
        raise NotImplementedError(self)

    def __getitem__(self, index):
        """Returns the ``event`` at position ``index`` in this queue."""
        raise NotImplementedError(self)

    def __bool__(self):
        """Returns ``False`` if this queue is empty and ``True`` otherwise."""
        raise NotImplementedError(self)


class FIFO(deque):
    """Simple "First In, First Out" queue, which may be bounded by ``maxlen``.
    """

    def append(self, event):
        if self.maxlen is not None and len(self) >= self.maxlen:
            raise ValueError('Cannot append event. Queue is full.')

        super(FIFO, self).append(event)


class LIFO(deque):
    """Simple "Last In, First Out" queue, which may be bounded by
    ``maxlen``."""

    def append(self, event):
        if self.maxlen is not None and len(self) >= self.maxlen:
            raise ValueError('Cannot append event. Queue is full.')

        self.appendleft(event)


class SortedQueue(list):
    """Queue that sorts events by their ``key`` attribute."""
    def __init__(self, maxlen=None):
        super(SortedQueue, self).__init__()
        self.maxlen = maxlen

    def append(self, item):
        if self.maxlen is not None and len(self) >= self.maxlen:
            raise ValueError('Cannot append event. Queue is full.')

        # TODO Use heapsort?
        super(SortedQueue, self).append(item)
        super(SortedQueue, self).sort(key=lambda e: e.key)
