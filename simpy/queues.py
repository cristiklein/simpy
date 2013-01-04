"""
This modules contains some queues that can be used with SimPy's
resources, namely a :class:`FIFO` and a :class:`LIFO` queue as well as a
:class:`Priority` queue.

"""
from collections import deque
from heapq import heappop, heappush, heapify
from itertools import count


class Queue(object):
    """Abstract base queue class for SimPy. It can't be used directly.

    Deriving classes have to implement :meth:`pop()`, :meth:`push()` and
    :meth:`peek()`.

    Its internal data store is a :class:`~collections.deque`.

    The Queue implements the :meth:`~object.__len__()`,
    :meth:`~object.__iter__()` and :meth:`~object.__delitem__()`
    methods.

    """
    def __init__(self):
        self._data = deque()

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __delitem__(self, key):
        del self._data[key]

    def pop(self):
        """Get and remove an item from the Queue.

        Raise a :exc:`IndexError` if the Queue is empty.

        """
        raise NotImplemented

    def push(self, item):
        """Append ``item`` to the queue."""
        raise NotImplemented

    def peek(self):
        """Get (but don't remove) the same item as :meth:`pop()` would do.

        Raise a :exc:`IndexError` if Queue is empty.

        """
        raise NotImplemented


class FIFO(Queue):
    """Simple "First In, First Out" queue, based on :class:`Queue`."""

    def pop(self):
        """Remove and return an element from the left side of the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._data.popleft()

    def push(self, item):
        """Append ``item`` to the right side of the queue."""
        return self._data.append(item)

    def peek(self):
        """Return, but don't remove, an element from the left side of
        the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._data[0]


class LIFO(Queue):
    """Simple "Last In, First Out" queu, based on :class:`Queue`."""

    def pop(self):
        """Remove and return an element from the right side of the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._data.pop()

    def push(self, item):
        """Append ``item`` to the right side of the queue."""
        return self._data.append(item)

    def peek(self):
        """Return, but don't remove, an element from the right side of
        the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self[-1]


class Priority(Queue):
    """Simple priority queue, based on :class:`Queue`.

    It uses a heap queue (:mod:`heapq`) as internal data store.

    """
    def __init__(self):
        super(Priority, self).__init__()
        self._data = []
        self._item_id = count()

    def __iter__(self):
        return (item for _, _, item in self._data)

    def __delitem__(self, key):
        del self._data[key]
        heapify(self._data)  # "del" might have corrupted the heap order

    def pop(self):
        """Remove and return the smallest element from the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return heappop(self._data)[-1]

    def push(self, item, priority=0):
        """Push ``item`` with ``priority`` onto the heap, maintain the
        heap invariant.

        A higher value for ``priority`` means a higher priority. The
        default is ``0``.

        """
        heappush(self._data, (-priority, next(self._item_id), item))

    def peek(self):
        """Return, but don't remove, the smallest element from the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._data[0][-1]
