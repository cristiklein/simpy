"""
The ``simpy`` module provides SimPy's end-user API. It therefore
aggregates Simpy's various classes and methods:

Core classes
------------

* :class:`~simpy.core.Environment`: SimPy's central class. It contains
  the simulation's state and lets the PEMs interact with it (i.e.,
  schedule events).

* :class:`~simpy.core.Interrupt`: This exception is thrown into
  a process if it gets interrupted by another one.


Resources
---------

- :class:`~simpy.resources.Resource`: Can be used by a limited number of
  processes at a time (e.g., a gas station with a limited number of fuel
  pumps).

- :class:`~simpy.resources.Container`: Models the production and
  consumption of a homogeneous, undifferentiated bulk. It may either be
  continuous (like water) or discrete (like apples).

- :class:`~simpy.resources.Store`: Allows the production and consumption
  of discrete Python objects.


Queues
------

- :class:`~simpy.queues.FIFO`: A simple FIFO queue.
- :class:`~simpy.queues.LIFO`: A simple LIFO queue.
- :class:`~simpy.queues.Priority`: A :mod:`heapq`-based priority queue.


Monitoring
----------

*[Not yet implemented]*


Other
-----

.. autofunction:: test

.. - :func:`test`: Run the test suite on the installed copy of Simpy.

"""
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

from simpy.core import Environment, Process, Interrupt, simulate, step, peek
from simpy.queues import FIFO, LIFO, Priority
from simpy.resources import Resource, Container, Store


__all__ = [
    'test',
    'Environment', 'Interrupt', 'peek', 'step', 'simulate',
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
