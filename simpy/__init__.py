"""
The ``simpy`` module provides SimPy's end-user API. It therefore
aggregates Simpy's various classes and methods:


Core classes and functions
--------------------------

.. currentmodule:: simpy.core

- :class:`Environment`: SimPy's central class. It contains
  the simulation's state and lets the PEMs interact with it (i.e.,
  schedule events).
- :class:`Process`: This class represents a PEM while
  it is executed in an environment. An instance of it is returned by
  :meth:`Environment.start()`. It inherits
  :class:`BaseEvent`.
- :class:`Interrupt`: This exception is thrown into a process if it gets
  interrupted by another one.
- :func:`peek()`: Return the next event's time.
- :func:`step()`: Process the next event.
- :func:`simulate()`: Execute the simulation until a given time.


Resources
---------

.. currentmodule:: simpy.resources

- :class:`Resource`: Can be used by a limited number of processes at a
  time (e.g., a gas station with a limited number of fuel pumps).
- :class:`Container`: Models the production and consumption of a
  homogeneous, undifferentiated bulk. It may either be continuous (like
  water) or discrete (like apples).
- :class:`Store`: Allows the production and consumption of discrete
  Python objects.


Queues
------

.. currentmodule:: simpy.queues

- :class:`FIFO`: A simple FIFO queue.
- :class:`LIFO`: A simple LIFO queue.
- :class:`Priority`: A :mod:`heapq`-based priority queue.


Monitoring
----------

.. currentmodule:: simpy.monitoring

*[Not yet implemented]*


Other
-----

.. currentmodule:: simpy

.. autofunction:: test

.. - :func:`test`: Run the test suite on the installed copy of Simpy.

"""
from simpy.core import Environment, Interrupt, Process, peek, step, simulate
from simpy.queues import FIFO, LIFO, Priority
from simpy.resources import Resource, Container, Store


__all__ = [
    'test',
    'Environment', 'Interrupt', 'Process', 'peek', 'step', 'simulate',
    'FIFO', 'LIFO', 'Priority',
    'Resource', 'Container', 'Store',
]
__version__ = '3.0a1'


def test():
    """Runs SimPy's test suite via `py.test <http://pytest.org/latest/>`_."""
    import os.path
    try:
        import mock
        import pytest
    except ImportError:
        print('You need pytest and mock to run the tests. '
              'Try "pip install pytest mock".')
    else:
        pytest.main([os.path.dirname(__file__)])
