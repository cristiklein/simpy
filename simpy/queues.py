"""
This modules contains some queues that can be used with SimPy's
resources, namely a :class:`FIFO` and a :class:`LIFO` queue as well as a
:class:`Priority` queue.

"""
from collections import deque


class Queue(object):
    """Abstract base queue class for SimPy. It can't be used directly.

    Queues can have a maxium length that can be specified via the
    ``maxlen`` parameter which defaults to ``0`` (unbound).

    Deriving classes have to implement :meth:`pop()`, :meth:`push()` and
    :meth:`peek()`.

    Its internal data store is a :class:`~collections.deque`.

    The Queue implements the :meth:`~object.__len__()` method.

    """
    def __init__(self, maxlen=0):
        self.maxlen = maxlen
        """The maximum length of the queue."""

        self._events = deque()

    def __len__(self):
        return len(self._events)

    def pop(self):
        """Get and remove an event from the Queue.

        Must be implemented by subclasses.

        Raise an :exc:`IndexError` if the Queue is empty.

        """
        raise NotImplemented

    def push(self, event):
        """Append ``event`` to the queue.

        Must be implemented by subclasses.

        Raise a :exc:`ValueError` if the queue's max. length is reached.

        """
        raise NotImplemented

    def peek(self):
        """Get (but don't remove) the same event as :meth:`pop()` would do.

        Must be implemented by subclasses.

        Raise an :exc:`IndexError` if Queue is empty.

        """
        raise NotImplemented

    def remove(self, event):
        """Remove ``event`` from the queue.

        Raise a :exc:`ValueError` if ``event`` is not in the queue.

        """
        self._events.remove(event)

    def _check_push(self):
        """Raise a :exc:`ValueError` if the queue's max. length is reached."""
        if self.maxlen and len(self._events) >= self.maxlen:
            raise ValueError('Cannot push. Queue is full.')


class FIFO(Queue):
    """Simple "First In, First Out" queue, based on :class:`Queue`."""

    def pop(self):
        """Remove and return an element from the left side of the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._events.popleft()

    def push(self, event):
        """Append ``event`` to the right side of the queue."""
        super(FIFO, self)._check_push()
        self._events.append(event)

    def peek(self):
        """Return, but don't remove, an element from the left side of
        the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._events[0]


class LIFO(Queue):
    """Simple "Last In, First Out" queu, based on :class:`Queue`."""

    def pop(self):
        """Remove and return an element from the right side of the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._events.pop()

    def push(self, event):
        """Append ``event`` to the right side of the queue."""
        super(LIFO, self)._check_push()
        return self._events.append(event)

    def peek(self):
        """Return, but don't remove, an element from the right side of
        the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._events[-1]


class Priority(Queue):
    """Simple priority queue, based on :class:`Queue`.

    It uses a heap queue (:mod:`heapq`) as internal data store.

    """
    def __init__(self, maxlen=0):
        super(Priority, self).__init__(maxlen)
        self._events = []

    def pop(self):
        """Remove and return the smallest element from the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._events.pop(0)

    def push(self, event):
        """Push ``event`` with ``priority`` onto the heap, maintain the
        heap invariant.

        A higher value for ``priority`` means a higher priority. The
        default is ``0``.

        """
        super(Priority, self)._check_push()
        self._events.append(event)
        self._events.sort(key=lambda event: event.key)

    def peek(self):
        """Return, but don't remove, the smallest element from the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._events[0]
