"""
The ``simpy`` module provides SimPy's end-user API. It therefore
aggregates Simpy's various classes and methods:

Core classes
------------

* :class:`~simpy.core.Simulation`: SimPy's central class that starts
  the processes and performs the simulation.

* :class:`~simpy.core.Interrupt`: This exception is thrown into
  a process if it gets interrupted by another one.

The following classes should not be imported directly:

* :class:`~simpy.core.Context`: An instance of that class is created by
  :class:`~simpy.core.Simulation` and passed to every PEM that is
  started.

* :class:`~simpy.core.Process`: An instance of that class is returned by
  :meth:`simpy.core.Simulation.start` and
  :meth:`simpy.core.Context.start`.


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
from simpy.core import Simulation, Interrupt
from simpy.queues import FIFO, LIFO, Priority
from simpy.resources import Resource, Container, Store


__all__ = ['Simulation', 'Interrupt', 'test', 'FIFO', 'LIFO', 'Priority',
           'Resource', 'Container', 'Store']
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
