"""
This modules contains some queues that can be used with SimPy's
resources, namely a :class:`FIFO` and a :class:`LIFO` queue as well as a
:class:`Priority` queue.

"""
from collections import deque
from heapq import heappop, heappush


class FIFO(deque):
    """Simple "First In, First Out" queue.

    It's based on :class:`deque`; :meth:`pop` removes from the left
    side, :meth:`push` appends to the right side.

    """
    def pop(self):
        """Remove and return an element from the left side of the queue.

        Raise an :class:`IndexError` if no elements are present.

        """
        return super(FIFO, self).popleft()

    def push(self, item):
        """Append *item* to the right side of the queue."""
        return super(FIFO, self).append(item)

    def peek(self):
        """Return, but don't remove, an element from the left side of
        the queue.

        Raise an :class:`IndexError` if no elements are present.

        """
        return self[0]


class LIFO(deque):
    """Simple "Last In, First Out" queue.

    It's based on :class:`deque`; :meth:`pop` removes from the right
    side, :meth:`push` appends to the right side.

    """
    def pop(self):
        """Remove and return an element from the right side of the queue.

        Raise an :class:`IndexError` if no elements are present.

        """
        return super(LIFO, self).pop()

    def push(self, item):
        """Append *item* to the right side of the queue."""
        return super(LIFO, self).append(item)

    def peek(self):
        """Return, but don't remove, an element from the right side of
        the queue.

        Raise an :class:`IndexError` if no elements are present.

        """
        return self[-1]


class Priority(list):
    """Simple priority queue.

    It's based on a heap queue (:mod:`heapq`); :meth:`pop` removes the
    smallest item, :meth:`push` always maintains the heap properties.

    """
    def pop(self):
        """Remove and return the smallest element from the queue.

        Raise an :class:`IndexError` if no elements are present.

        """
        return heappop(self)[1]

    def push(self, item, priority):
        """Push *item* with *priority* onto the heap, maintain the heap
        invariant.

        """
        heappush(self, (priority, item))

    def peek(self):
        """Return, but don't remove, the smallest element from the queue.

        Raise an :class:`IndexError` if no elements are present.

        """
        return self[0]
