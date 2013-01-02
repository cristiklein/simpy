"""
This modules contains some queues that can be used with SimPy's
resources, namely a :class:`FIFO` and a :class:`LIFO` queue as well as a
:class:`Priority` queue.

"""
from collections import deque
from heapq import heappop, heappush


class Queue(object):
    """Abstract base queue class for SimPy. It can't be used directly.

    Deriving classes have to implement :meth:`pop()`, :meth:`push()` and
    :meth:`peek()`.

    Its internal data store is a :class:`~collections.deque`.

    The Queue supports Python's ``in`` keyword and :func:`len()`.

    """
    def __init__(self):
        self._data = deque()

    def __len__(self):
        return len(self._data)

    def __contains__(self, item):
        return item in self._data

    def remove(self, item):
        """Remove ``item`` from the queue.

        Raise a :exc:`ValueError` if ``item`` is not in the queue.

        """
        self._data.remove(item)

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

    def __contains__(self, item):
        for prio, elem in self._data:
            if elem == item:
                return True
        return False

    def remove(self, item):
        for i in range(len(self._data)):
            if self._data[i][1] == item:
                del self._data[i]
                return
        raise ValueError('Priority.remove(x): x not in list.')

    def pop(self):
        """Remove and return the smallest element from the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return heappop(self._data)[1]

    def push(self, item, priority=1):
        """Push ``item`` with ``priority`` onto the heap, maintain the
        heap invariant.

        """
        heappush(self._data, (priority, item))

    def peek(self):
        """Return, but don't remove, the smallest element from the queue.

        Raise an :exc:`IndexError` if no elements are present.

        """
        return self._data[0][1]
