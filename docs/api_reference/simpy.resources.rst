==================================================
``simpy.resources`` --- Shared resource primitives
==================================================

SimPy supports three primitives to share and synchronize the use of resources
between processes:


.. autosummary::

    ~simpy.resources.resource
    ~simpy.resources.container
    ~simpy.resources.store

All of these modules are derived from the base classes in the
:mod:`~simpy.resources.base`. The classes in this module is also meant to
support the implementation of custom resource primitives.


Resources --- ``simpy.resources.resource``
==========================================

.. automodule:: simpy.resources.resource
    :members:

Containers --- ``simpy.resources.container``
============================================

.. automodule:: simpy.resources.container
    :members:

Stores --- ``simpy.resources.store``
====================================

.. automodule:: simpy.resources.store
    :members:

Base classes --- ``simpy.resources.base``
=========================================

.. automodule:: simpy.resources.base
    :members:
