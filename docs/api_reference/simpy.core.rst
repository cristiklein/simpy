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
   :members: name, callbacks, is_alive, target, interrupt

.. autoclass:: Interrupt
   :members: cause

.. autoclass:: BaseEvent
   :members: callbacks, is_alive

.. autoclass:: Event
   :members: callbacks, is_alive, succeed, fail

.. autoclass:: Timeout
   :members: callbacks, is_alive
