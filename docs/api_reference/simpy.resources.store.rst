==================================================
``simpy.resources.store`` --- Store type resources
==================================================

.. automodule:: simpy.resources.store

.. autoclass:: Store

    .. autoattribute:: capacity

    .. attribute:: items

        List of the items within the store.

    .. method:: put(item)

        Create a new :class:`StorePut` event.

    .. method:: get()

        Create a new :class:`StoreGet` event.

.. autoclass:: FilterStore

    .. method:: get(filter=lambda item: True)

        Create a new :class:`FilterStoreGet` event.

.. autoclass:: StorePut

.. autoclass:: StoreGet

.. autoclass:: FilterStoreGet(resource, filter=lambda item: True)

    .. attribute:: filter

        The filter function to use.

.. autoclass:: FilterQueue

    .. automethod:: __getitem__
    .. automethod:: __bool__
    .. automethod:: __nonzero__
