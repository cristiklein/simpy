import pytest

from simpy.queues import FIFO, LIFO, Priority


IN = 0
OUT = 1
ITER = 2
REMOVE = 3

seq_fifo = [
    (OUT, IndexError),
    (IN, 2), (IN, 3), (IN, 1),
    (ITER, [2, 3, 1]),
    (OUT, 2), (OUT, 3),
    (IN, 4), (IN, 5),
    (REMOVE, 1),
    (OUT, 1), (OUT, 5),
    (OUT, IndexError),
]

seq_lifo = [
    (OUT, IndexError),
    (IN, 2), (IN, 3), (IN, 1),
    (ITER, [2, 3, 1]),
    (OUT, 1), (OUT, 3),
    (IN, 4), (IN, 5),
    (REMOVE, 1),
    (OUT, 5), (OUT, 2),
    (OUT, IndexError),
]

seq_priority = [
    (OUT, IndexError),
    (IN, 2), (IN, 1), (IN, 3),
    (ITER, [3, 1, 2]),
    (OUT, 3), (OUT, 2),
    (IN, 4), (IN, 1), (IN, 5),
    (REMOVE, 2),
    (OUT, 5), (OUT, 4), (OUT, 1),
    (OUT, IndexError),
]


@pytest.mark.parametrize(('Queue', 'seq'), [
    (FIFO, seq_fifo),
    (LIFO, seq_lifo),
    (Priority, seq_priority),
])
def test_queues(Queue, seq):
    """Tests for SimPy's build-in queue types."""
    q = Queue()

    for action, item in seq:
        if item is IndexError:
            try:
                q.pop()
                pytest.fail('Onoes')
            except IndexError:
                pass
            # pytest.raises(IndexError, q.pop)

        elif action is IN:
            orig_len = len(q)
            if isinstance(q, Priority):
                q.push(item, item)
            else:
                q.push(item)
            assert item in q
            assert len(q) == orig_len + 1
        elif action is ITER:
            assert [i for i in q] == item
        elif action is REMOVE:
            orig_len = len(q)
            del q[item]
            assert len(q) == orig_len - 1
        else:
            val = q.pop()
            assert val == item
