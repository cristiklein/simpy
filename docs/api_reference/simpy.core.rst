==========================================
``simpy.core`` --- SimPy's core components
==========================================


.. automodule:: simpy.core

.. data:: PENDING = object()

    Unique object to identify pending values of events.

.. autofunction:: peek
.. autofunction:: step
.. autofunction:: simulate
.. autofunction:: all_events
.. autofunction:: any_event

.. autoclass:: Environment

    .. autoattribute:: active_process
    .. autoattribute:: now
    .. automethod:: exit

    .. method:: event(self)

        Returns a new instance of :class:`Event`.

    .. method:: suspend(self)

        Convenience method. Also returns a new instance of :class:`Event`.

    .. method:: timeout(self, delay, value=None)

        Returns a new instance of :class:`Timeout`.

    .. method:: process(self, generator)

        Returns a new instance of :class:`Process`.

    .. method:: start(self, generator)

        Convenience method. Also returns a new instance of :class:`Process`.


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


.. autoclass:: Initialize

    .. attribute:: callbacks

        List of functions that are called when the event is processed.

    .. attribute:: env

        The :class:`Environment` the event lives in.


.. autoclass:: Scheduler
    :members:

    .. attribute:: queue

        A list with all currently scheduled events.

.. autoclass:: EmptySchedule

.. autoclass:: Interrupt
   :members: cause
