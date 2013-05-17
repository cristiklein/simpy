===========================================================
``simpy.resources.base`` --- Base classes for all resources
===========================================================

.. automodule:: simpy.resources.base

.. autoclass:: BaseResource

    .. method:: put()

        Create a new of :class:`Put` event.

    .. method:: get()

        Create a new of :class:`Get` event.

    .. attribute:: put_queue

        Queue/list of events waiting to get something out of the resource.

    .. attribute:: get_queue

        Queue/list of events waiting to put something into the resource.

    .. autoattribute:: PutQueue

    .. autoattribute:: GetQueue

    .. automethod:: _do_put

    .. automethod:: _do_get


.. autoclass:: Put
    :members:

.. autoclass:: Get
    :members:
