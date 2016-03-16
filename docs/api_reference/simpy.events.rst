=====================================
``simpy.events`` --- Core event types
=====================================

.. automodule:: simpy.events

   .. autodata:: PENDING
      :annotation: = object()

   .. autodata:: URGENT
   .. autodata:: NORMAL

   .. autoclass:: Event
      :inherited-members:

   .. autoclass:: Timeout
      :inherited-members:

   .. autoclass:: Initialize
      :inherited-members:

   .. autoclass:: Interruption
      :inherited-members:

   .. autoclass:: Process
      :inherited-members:

   .. autoclass:: Condition
      :inherited-members:

   .. autoclass:: AllOf
      :inherited-members:
      :exclude-members: all_events, any_events

   .. autoclass:: AnyOf
      :inherited-members:
      :exclude-members: all_events, any_events

   .. autoclass:: ConditionValue
      :members:

   .. autoclass:: Interrupt
      :members:
