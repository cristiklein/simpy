# encoding: utf-8
"""
With SimPy, simulating is fun again!

"""
from simpy.core import Simulation, Interrupt
from simpy.queues import FIFO, LIFO, Priority
from simpy.resources import Resource, Container, Store


__all__ = ['Simulation', 'Interrupt', 'test', 'FIFO', 'LIFO', 'Priority',
           'Resource', 'Container', 'Store']
__version__ = '3.0a1'


def test():
    """Runs SimPy’s test suite via *py.test*."""
    import os.path
    try:
        import mock
        import pytest
    except ImportError:
        print('You need pytest and mock to run the tests. '
              'Try "pip install pytest mock".')
    else:
        pytest.main([os.path.dirname(__file__)])
