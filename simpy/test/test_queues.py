import pytest

from simpy.resources.queues import FIFO, LIFO, SortedQueue


IN = 0
OUT = 1

seq_fifo = [
    (OUT, IndexError),
    (IN, 2), (IN, 3), (IN, 1),
    (OUT, 2), (OUT, 3),
    (IN, 4),
    (OUT, 1), (OUT, 4),
    (OUT, IndexError),
]

seq_lifo = [
    (OUT, IndexError),
    (IN, 2), (IN, 3), (IN, 1),
    (OUT, 1), (OUT, 3),
    (IN, 4),
    (OUT, 4), (OUT, 2),
    (OUT, IndexError),
]

seq_priority = [
    (OUT, IndexError),
    (IN, 2), (IN, 1), (IN, 3),
    (OUT, 1), (OUT, 2),
    (IN, 4), (IN, 1),
    (OUT, 1), (OUT, 3), (OUT, 4),
    (OUT, IndexError),
]


class Item(object):
    def __init__(self, i):
        self.key = i

    def __eq__(self, other):
        return self.key == other.key


@pytest.mark.parametrize(('Queue', 'seq'), [
    (FIFO, seq_fifo),
    (LIFO, seq_lifo),
    (SortedQueue, seq_priority),
])
def test_queues(Queue, seq):
    """Tests for SimPy's build-in queue types."""
    q = Queue()

    for action, item in seq:
        item = Item(item)
        if item.key is IndexError:
            pytest.raises(IndexError, q.pop)
        elif action is IN:
            orig_len = len(q)
            q.push(item)
            assert len(q) == orig_len + 1
        else:
            peek = q.peek()
            val = q.pop()
            assert peek == item
            assert val == item


@pytest.mark.parametrize('Queue', [
    FIFO,
    LIFO,
    SortedQueue,
])
def test_remove(Queue):
    q = Queue()
    q.push(Item(1))
    q.push(Item(3))
    q.push(Item(2))

    assert len(q) == 3
    q.remove(Item(3))
    assert len(q) == 2

    pytest.raises(ValueError, q.remove, Item(3))


@pytest.mark.parametrize('Queue', [
    FIFO,
    LIFO,
    SortedQueue,
])
def test_maxlen(Queue):
    q = Queue(maxlen=2)
    q.push(Item(1))
    q.push(Item(2))
    pytest.raises(ValueError, q.push, Item(3))
