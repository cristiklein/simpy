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

    .. attribute:: callbacks

        List of functions that are called when the event is processed.

    .. attribute:: env

        The :class:`Environment` the event lives in.

    .. attribute:: name

        Optional name for this event. Used for :class:`str` / :func:`repr` if
        not ``None``.

    .. autoattribute:: triggered
    .. autoattribute:: processed
    .. autoattribute:: value
    .. automethod:: succeed
    .. automethod:: fail


.. autoclass:: Process

    .. attribute:: callbacks

        List of functions that are called when the event is processed.

    .. attribute:: env

        The :class:`Environment` the event lives in.

    .. attribute:: name

        Optional name for this event. Used for :class:`str` / :func:`repr` if
        not ``None``.

    .. autoattribute:: target
    .. autoattribute:: is_alive
    .. automethod:: interrupt


.. autoclass:: Timeout

    .. attribute:: callbacks

        List of functions that are called when the event is processed.

    .. attribute:: env

        The :class:`Environment` the event lives in.

    .. attribute:: name

        Optional name for this event. Used for :class:`str` / :func:`repr` if
        not ``None``.


.. autoclass:: Condition

    .. attribute:: callbacks

        List of functions that are called when the event is processed.

    .. attribute:: env

        The :class:`Environment` the event lives in.

    .. attribute:: name

        Optional name for this event. Used for :class:`str` / :func:`repr` if
        not ``None``.

    .. automethod:: all_events
    .. automethod:: any_events


.. autoclass:: Initialize

    .. attribute:: callbacks

        List of functions that are called when the event is processed.

    .. attribute:: env

        The :class:`Environment` the event lives in.


.. autoclass:: AllOf

.. autoclass:: AnyOf

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
