==========================================
``simpy.core`` --- SimPy's core components
==========================================


.. automodule:: simpy.core

.. autofunction:: peek
.. autofunction:: step
.. autofunction:: simulate

.. autoclass:: Environment
    :members:

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

.. autoclass:: Process
   :members: callbacks, env, is_alive, target, interrupt

.. autoclass:: Interrupt
   :members: cause

.. autoclass:: Event
   :members: callbacks, env, succeed, fail

.. autoclass:: Timeout
   :members: callbacks, env

.. autoclass:: Condition
   :members: callbacks, env

.. autofunction:: all_events
.. autofunction:: any_event
