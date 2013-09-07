==========================================
``simpy.core`` --- SimPy's core components
==========================================

.. automodule:: simpy.core


Environments
============

.. autoclass:: BaseEnvironment
    :members:

.. autoclass:: Environment
    :members:
    :inherited-members:


Events
======

.. autoclass:: Event(env, value=PENDING, name=None)
    :members:

.. autoclass:: Process
    :members:

.. autoclass:: Timeout
    :members:

.. autoclass:: Condition
    :members:

.. autoclass:: AllOf
    :members:

.. autoclass:: AnyOf
    :members:

.. autoclass:: Initialize
    :members:


Miscellaneous (Interrupt and constants)
=======================================

.. autoclass:: BoundClass
    :members:

.. autoclass:: EmptySchedule

.. autoclass:: Interrupt
   :members: cause

.. autodata:: Infinity
.. autodata:: PENDING
.. autodata:: HIGH_PRIORITY
.. autodata:: DEFAULT_PRIORITY
.. autodata:: LOW_PRIORITY
