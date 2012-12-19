==========================================
``simpy.core`` --- SimPy's Core Components
==========================================


.. automodule:: simpy.core

.. autofunction:: peek
.. autofunction:: step
.. autofunction:: simulate

.. autoclass:: Environment
   :members: active_process, now, start, exit, event, timeout, suspend

.. autoclass:: Process
   :members: callbacks, env, is_alive, target, interrupt

.. autoclass:: Interrupt
   :members: cause

.. autoclass:: BaseEvent
   :members: callbacks, env

.. autoclass:: Event
   :members: callbacks, env, succeed, fail

.. autoclass:: Timeout
   :members: callbacks, env
