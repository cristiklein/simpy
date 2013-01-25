"""
This module contains all event types need by SimPy's built-in resources:

- :class:`ResourceEvent`: Base class for all resource events and default
  event type used by :class:`~simpy.resources.Resource`.

- :class:`PriorityResourceEvent`: Resource event with a user defined
  priority.

- :class:`ContainerEvent`: Event type used by
  :class:`~simpy.resources.Container`.

- :class:`StoreEvent`: Event type used by
  :class:`~simpy.resources.Store`.

"""
from simpy.core import Event


class ResourceEvent(Event):
    """Simple resource event used by default by
    :class:`~simpy.resources.Resource`.

    Resource events can be used as context managers that automatically
    release or cancel resource requests when the context manager is
    left---even after an exception or interrupt was raised:

    .. code-block:: python

        with resource.request() as request:
            yield request

    Events also define a :meth:`key()` function that is used to sort
    events.

    *ResouceEvents* are sorted by creation time and are thus queued in a
    *FIFO (First in, first out)* way.

    """
    def __init__(self, resource, proc):
        env = resource._env
        super(ResourceEvent, self).__init__(env)

        self._resource = resource
        self._proc = proc

        self.time = env.now
        """Time that this event was created on."""

    def __str__(self):
        return '%s(%r)' % (self.__class__.__name__, self._proc)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        self._resource.release(self)

    @property
    def key(self):
        """The default implementation sorts events by creation time."""
        return self.time


class PriorityResourceEvent(ResourceEvent):
    """Resource event with a user defined priority.

    This event sorts by a *priority* and can be used for preemptive
    resources or to queue events by priority instead of FIFO. The
    priority has to be passed to
    :meth:`simpy.resources.Resource.request()` or
    :class:`simpy.resources.Store.get()` and the like.

    Note, a smaller value for ``priority`` means a higher priority
    (comparable to *Unix process priorities*, *first class / second
    class*, *primary / secondary* etc.). If the priority of two events
    is equal, the creation time will used as secondary sort key.

    If the you set *preempt* to ``False``, no preemption will happen
    even if the priority would be high enough.

    """
    def __init__(self, resource, proc, priority, preempt=True):
        super(PriorityResourceEvent, self).__init__(resource, proc)
        self.priority = priority
        self.preempt = preempt

    def __str__(self):
        return '%s(%r, priority=%s)' % (self.__class__.__name__, self._proc,
                                        self.priority)

    @property
    def key(self):
        """Sort events by *(priority, time)*"""
        return self.priority, self.time


class ContainerEvent(ResourceEvent):
    """A *ContainerEvent* is returned by
    :meth:`simpy.resources.Container.get()` and
    :meth:`simpy.resources.Container.put()`:

    .. code-block:: python

        with container.get(42) as request:
            yield request

    It inherits :class:`ResourceEvent`.

    """
    def __init__(self, container, proc, amount):
        super(ContainerEvent, self).__init__(container, proc)

        self.amount = amount
        """The amount that was requested from or for the container."""

    def __str__(self):
        return '%s(%r, amount=%s)' % (self.__class__.__name__, self._proc,
                                      self.amount)


class StoreEvent(ResourceEvent):
    """A *ContainerEvent* is returned by :meth:`simpy.resources.Store.get()`
    and :meth:`simpy.resources.Store.put()`:

    .. code-block:: python

        with container.get(42) as request:
            yield request

    It inherits :class:`ResourceEvent`.

    """
    def __init__(self, store, proc, item=None):
        super(StoreEvent, self).__init__(store, proc)

        self.item = item
        """The item to store or ``None``."""

    def __str__(self):
        return '%s(%r, item=%r)' % (self.__class__.__name__, self._proc,
                                    self.item)
