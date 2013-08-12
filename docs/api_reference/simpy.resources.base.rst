===========================================================
``simpy.resources.base`` --- Base classes for all resources
===========================================================

.. automodule:: simpy.resources.base

.. autoclass:: BaseResource

    .. attribute:: PutQueue

        The type to be used for the :attr:`put_queue`. This can either be
        a plain :class:`list` (default) or a subclass of it.

    .. attribute:: GetQueue

        The type to be used for the :attr:`get_queue`. This can either be
        a plain :class:`list` (default) or a sublcass of it.

    .. attribute:: put_queue

        Queue/list of events waiting to get something out of the resource.

    .. attribute:: get_queue

        Queue/list of events waiting to put something into the resource.

    .. method:: put()

        Create a new of :class:`Put` event.

    .. method:: get()

        Create a new of :class:`Get` event.

    .. automethod:: _do_put

    .. automethod:: _do_get


.. autoclass:: Put
    :members:

.. autoclass:: Get
    :members:
