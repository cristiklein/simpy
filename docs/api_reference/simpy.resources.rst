=======================================================
``simpy.resources`` --- SimPy's built-in resource types
=======================================================


.. automodule:: simpy.resources

.. autoclass:: Resource(env, capacity, event_type=ResourceEvent, user_type=Users)
    :inherited-members:

.. autoclass:: PreemptiveResource(env, capacity, event_type=PriorityResourceEvent)
    :inherited-members:

.. autoclass:: Container(env, capacity=Infinity, init=0, event_type=ContainerEvent)
    :inherited-members:

.. autoclass:: Store(env, capacity=Infinity, item_q_type=FIFO, event_type=StoreEvent)
    :inherited-members:

.. autoclass:: BaseContainer
    :inherited-members:
