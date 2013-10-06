==========================================
``simpy.core`` --- SimPy's core components
==========================================

.. automodule:: simpy.core

.. autoclass:: BaseEnvironment
    :members:

.. autoclass:: Environment

    .. autoattribute:: now
    .. autoattribute:: active_process

    .. method:: process(generator)

        Create a new :class:`~simpy.events.Process` instance for *generator*.

    .. method:: timeout(delay, value=None)

        Return a new :class:`~simpy.events.Timeout` event with a *delay* and,
        optionally, a *value*.

    .. method:: event()

        Return a new :class:`~simpy.events.Event` instance. Yielding this event
        suspends a process until another process triggers the event.

    .. method:: all_of(events)

        Return a new :class:`~simpy.events.AllOf` condition for a list of
        *events*.

    .. method:: any_of(events)

        Return a new :class:`~simpy.events.AnyOf` condition for a list of
        *events*.

    .. automethod:: exit
    .. automethod:: schedule
    .. automethod:: peek
    .. automethod:: step
    .. automethod:: run

.. autoclass:: BoundClass
    :members:

.. autoclass:: EmptySchedule

.. autodata:: Infinity
