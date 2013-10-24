"""
This module contains all :class:`Container` like resources.

Containers model the production and consumption of a homogeneous,
undifferentiated bulk. It may either be continuous (like water) or discrete
(like apples).

For example, a gasoline station stores gas (petrol) in large tanks.  Tankers
increase, and refuelled cars decrease, the amount of gas in the station's
storage tanks.

"""
from simpy.core import BoundClass
from simpy.resources import base


class ContainerPut(base.Put):
    """An event that puts *amount* into the *container*. The event is triggered
    as soon as there's enough space in the *container*.

    Raise a :exc:`ValueError` if ``amount <= 0``.

    """
    def __init__(self, container, amount):
        if amount <= 0:
            raise ValueError('amount(=%s) must be > 0.' % amount)
        #: The amount to be put into the container.
        self.amount = amount
        """The amount to be put into the container."""

        super(ContainerPut, self).__init__(container)


class ContainerGet(base.Get):
    """An event that gets *amount* from the *container*. The event is triggered
    as soon as there's enough content available in the *container*.

    Raise a :exc:`ValueError` if ``amount <= 0``.

    """
    def __init__(self, resource, amount):
        if amount <= 0:
            raise ValueError('amount(=%s) must be > 0.' % amount)
        self.amount = amount
        """The amount to be taken out of the container."""

        super(ContainerGet, self).__init__(resource)


class Container(base.BaseResource):
    """Models the production and consumption of a homogeneous, undifferentiated
    bulk. It may either be continuous (like water) or discrete (like apples).

    The *env* parameter is the :class:`~simpy.core.Environment` instance the
    container is bound to.

    The *capacity* defines the size of the container and must be a positive
    number (> 0). By default, a container is of unlimited size.  You can
    specify the initial level of the container via *init*. It must be >=
    0 and is 0 by default.

    Raise a :exc:`ValueError` if ``capacity <= 0``, ``init < 0`` or
    ``init > capacity``.

    """
    def __init__(self, env, capacity=float('inf'), init=0):
        super(Container, self).__init__(env)
        if capacity <= 0:
            raise ValueError('"capacity" must be > 0.')
        if init < 0:
            raise ValueError('"init" must be >= 0.')
        if init > capacity:
            raise ValueError('"init" must be <= "capacity".')

        self._capacity = capacity
        self._level = init

    @property
    def capacity(self):
        """The maximum capacity of the container."""
        return self._capacity

    @property
    def level(self):
        """The current level of the container (a number between ``0`` and
        ``capacity``).

        """
        return self._level

    put = BoundClass(ContainerPut)
    """Creates a new :class:`ContainerPut` event."""

    get = BoundClass(ContainerGet)
    """Creates a new :class:`ContainerGet` event."""

    def _do_put(self, event):
        if self._capacity - self._level >= event.amount:
            self._level += event.amount
            event.succeed()

    def _do_get(self, event):
        if self._level >= event.amount:
            self._level -= event.amount
            event.succeed()
