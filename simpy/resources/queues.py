"""
This modules contains some queues that can be used with SimPy's
resources, namely a :class:`FIFO` and a :class:`LIFO` queue as well as a
:class:`SortedQueue` queue.

"""
from collections import deque


Infinity = float('inf')


class Queue(object):
    """Abstract base queue class for SimPy. It can't be used directly.

    Queues can have a maxium length that can be specified via the
    ``maxlen`` parameter which defaults to ``0`` (unbound).

    Deriving classes have to implement :meth:`pop()`, :meth:`push()` and
    :meth:`peek()`.

    Its internal data store is a :class:`~collections.deque`.

    The Queue implements the :meth:`~object.__len__()` method.

    """
    def __init__(self, maxlen=Infinity):
        self.maxlen = maxlen
        """The maximum length of the queue."""

        self._items = deque()

    def __len__(self):
        return len(self._items)

    def pop(self):
        """Get and remove an item from the Queue.

        Must be implemented by subclasses.

        Raise an :exc:`IndexError` if the Queue is empty.

        """
        raise NotImplemented

    def push(self, item):
        """Append ``item`` to the queue.

        Must be implemented by subclasses.

        Raise a :exc:`ValueError` if the queue's max. length is reached.

        """
        raise NotImplemented

    def peek(self):
        """Get (but don't remove) the same item as :meth:`pop()` would do.

        Must be implemented by subclasses.

        Raise an :exc:`IndexError` if Queue is empty.

        """
        raise NotImplemented

    def remove(self, item):
        """Remove ``item`` from the queue.

        Raise a :exc:`ValueError` if ``item`` is not in the queue.

        """
        self._items.remove(item)


class FIFO(Queue):
    """Simple "First In, First Out" queue, based on :class:`Queue`."""

    def pop(self):
        """Remove and return an element from the left side of the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._items.popleft()

    def push(self, item):
        """Append ``item`` to the right side of the queue."""
        if len(self._items) >= self.maxlen:
            raise ValueError('Cannot push. Queue is full.')
        self._items.append(item)

    def peek(self):
        """Return, but don't remove, an element from the left side of
        the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._items[0]


class LIFO(Queue):
    """Simple "Last In, First Out" queu, based on :class:`Queue`."""

    def pop(self):
        """Remove and return an element from the right side of the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._items.pop()

    def push(self, item):
        """Append ``item`` to the right side of the queue."""
        if len(self._items) >= self.maxlen:
            raise ValueError('Cannot push. Queue is full.')
        return self._items.append(item)

    def peek(self):
        """Return, but don't remove, an element from the right side of
        the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._items[-1]


class SortedQueue(Queue):
    """Queue that sorts items by their ``key`` attribute, based on
    :class:`Queue`.

    """
    def __init__(self, maxlen=Infinity):
        super(SortedQueue, self).__init__(maxlen)
        self._items = []

    def pop(self):
        """Remove and return the smallest element from the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._items.pop(0)

    def push(self, item):
        """Add ``item`` to the queue and keep it sorted."""
        if len(self._items) >= self.maxlen:
            raise ValueError('Cannot push. Queue is full.')
        self._items.append(item)
        self._items.sort(key=lambda e: e.key)

    def peek(self):
        """Return, but don't remove, the smallest element from the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._items[0]
