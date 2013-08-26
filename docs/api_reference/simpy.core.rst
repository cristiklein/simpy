==========================================
``simpy.core`` --- SimPy's core components
==========================================


.. automodule:: simpy.core

Environments
============

.. autoclass:: Environment
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: BaseEnvironment
    :members:

Events
======

.. autoclass:: Event(env, value=PENDING, name=None)
    :members:

.. autoclass:: Process
    :members:
    :show-inheritance:

.. autoclass:: Timeout
    :members:
    :show-inheritance:

.. autoclass:: Condition
    :members:
    :show-inheritance:

.. autoclass:: Initialize
    :members:
    :show-inheritance:

.. autoclass:: AllOf
    :members:
    :show-inheritance:

.. autoclass:: AnyOf
    :members:
    :show-inheritance:

Miscellaneous (Interrupt and constants)
=======================================

.. autoclass:: EmptySchedule

.. autoclass:: Interrupt
   :members: cause

.. data:: Infinity = inf

    Convenience alias for infinity

.. data:: PENDING = object()

    Unique object to identify pending values of events

.. data:: HIGH_PRIORITY = 0

    Priority of interrupts and Intialize events

.. data:: DEFAULT_PRIORITY = 1

    Default priority used by events

.. data:: LOW_PRIORITY = 2

    Priority of timeouts
