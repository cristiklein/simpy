"""
The ``simpy`` module provides SimPy's end-user API. It aggregates Simpy's most
important classes and methods. This is purely for your convenience. You can of
course also access everything (and more!) via their actual submodules.


Core classes and functions
--------------------------

.. currentmodule:: simpy.core

- :class:`Environment`: SimPy's central class. It contains
  the simulation's state and lets the PEMs interact with it (i.e.,
  schedule events).

.. currentmodule:: simpy.events

- :class:`Interrupt`: This exception is thrown into a process if it gets
  interrupted by another one.


Resources
---------

.. currentmodule:: simpy.resources.resource

- :class:`Resource`: Can be used by a limited number of processes at a
  time (e.g., a gas station with a limited number of fuel pumps).

- :class:`PriorityResource`: Like :class:`Resource`, but waiting
  processes are sorted by priority.

- :class:`PreemptiveResource`: Version of :class:`Resource` with
  preemption.

.. currentmodule:: simpy.resources.container

- :class:`Container`: Models the production and consumption of a
  homogeneous, undifferentiated bulk. It may either be continuous (like
  water) or discrete (like apples).

.. currentmodule:: simpy.resources.store

- :class:`Store`: Allows the production and consumption of discrete
  Python objects.

- :class:`FilterStore`: Like :class:`Store`, but items taken out of it
  can be filtered with a user-defined function.


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
from pkgutil import extend_path

from simpy.core import Environment
from simpy.events import Interrupt
from simpy.resources.resource import (
    Resource, PriorityResource, PreemptiveResource)
from simpy.resources.container import Container
from simpy.resources.store import Store, FilterStore


__path__ = extend_path(__path__, __name__)
__all__ = [
    'test',
    'Environment',
    'Interrupt',
    'Resource', 'PriorityResource', 'PreemptiveResource',
    'Container',
    'Store', 'FilterStore',
]
__version__ = '3.0.4'


def test():
    """Runs SimPy's test suite via `py.test <http://pytest.org/latest/>`_."""
    import os.path
    try:
        import pytest
    except ImportError:
        print('You need pytest to run the tests. Try "pip install pytest".')
    else:
        pytest.main([os.path.dirname(__file__)])
