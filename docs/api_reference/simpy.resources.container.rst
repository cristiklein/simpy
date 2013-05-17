==========================================================
``simpy.resources.container`` --- Container type resources
==========================================================

.. automodule:: simpy.resources.container

.. autoclass:: Container

    .. method:: put(amount)

        Creates a new :class:`ContainerPut` event.

    .. method:: get(amount)

        Creates a new :class:`ContainerGet` event.

.. autoclass:: ContainerPut

    .. attribute:: amount

        The amount to be put into the container.

.. autoclass:: ContainerGet

    .. attribute:: amount

        The amount to be taken out of the container.
