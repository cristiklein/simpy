"""
Base classes of for Simpy's shared resource primitives.

:class:`BaseResource` defines the abstract base resource. It supports get and
put requests, which return :class:`Put` respectively :class:`Get` events. These
events are triggered once the request has been completed.
"""

from simpy.core import BoundClass
from simpy.events import Event


class Put(Event):
    """Generic event for requesting to put something into the *resource*.

    This event (and all of its subclasses) can act as context manager and can
    be used with the :keyword:`with` statement to automatically cancel the
    request if an exception (like an :class:`simpy.events.Interrupt` for
    example) occurs:

    .. code-block:: python

        with res.put(item) as request:
            yield request
    """

    def __init__(self, resource):
        super(Put, self).__init__(resource._env)
        self.resource = resource
        self.proc = self.env.active_process

        resource.put_queue.append(self)
        self.callbacks.append(resource._trigger_get)
        resource._trigger_put(None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cancel()

    def cancel(self):
        """Cancel this put request.

        This method has to be called if the put request must be aborted, for
        example if a process needs to handle an exception like an
        :class:`~simpy.events.Interrupt`.

        If the put request was created in a :keyword:`with` statement, this
        method is called automatically.
        """
        if not self.triggered:
            self.resource.put_queue.remove(self)


class Get(Event):
    """Generic event for requesting to get something from the *resource*.

    This event (and all of its subclasses) can act as context manager and can
    be used with the :keyword:`with` statement to automatically cancel the
    request if an exception (like an :class:`simpy.events.Interrupt` for
    example) occurs:

    .. code-block:: python

        with res.put(item) as request:
            yield request
    """

    def __init__(self, resource):
        super(Get, self).__init__(resource._env)
        self.resource = resource
        self.proc = self.env.active_process

        resource.get_queue.append(self)
        self.callbacks.append(resource._trigger_put)
        resource._trigger_get(None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cancel()

    def cancel(self):
        """Cancel this get request.

        This method has to be called if the get request must be aborted, for
        example if a process needs to handle an exception like an
        :class:`~simpy.events.Interrupt`.

        If the get request was created in a :keyword:`with` statement, this
        method is called automatically.
        """

        if not self.triggered:
            self.resource.get_queue.remove(self)


class BaseResource(object):
    """Abstract base class for a shared resource.

    You can :meth:`put()` something into the resources or :meth:`get()`
    something out of it. Both methods return an event that is triggered once
    the operation is completed. If a :meth:`put()` request cannot complete
    immediately (for example if the resource has reached a capacity limit) it
    is enqueued in the :attr:`put_queue` for later processing. Likewise for
    :meth:`get()` requests.

    Subclasses can customize the resource by:

    - providing different :attr:`PutQueue` and :attr:`GetQueue` types,
    - providing :class:`Put` respectively :class:`Get` events,
    - and implementing different request processing behaviour by
      :meth:`_do_get()` and :meth:`_do_put()`.
    """

    PutQueue = list
    """The type to be used for the :attr:`put_queue`. It is a plain
    :class:`list` by default. The type must support iteration and provide
    ``append()`` and ``remove()`` operations."""

    GetQueue = list
    """The type to be used for the :attr:`get_queue`. It is a plain
    :class:`list` by default. The type must support iteration and provide
    ``append()`` and ``remove()`` operations."""

    def __init__(self, env):
        self._env = env
        self.put_queue = self.PutQueue()
        """Queue of pending put requests."""
        self.get_queue = self.GetQueue()
        """Queue of pending get requests."""

        # Bind event constructors as methods
        BoundClass.bind_early(self)

    put = BoundClass(Put)
    """Request to put something into the resource and return a :class:`Put`
    event, which gets triggered once the request succeeds.
    """

    get = BoundClass(Get)
    """Request to get something from the resource and return a :class:`Get`
    event, which gets triggered once the request succeeds.
    """

    def _do_put(self, event):
        """Perform the *put* operation.

        This methods needs to be implemented by subclasses. It receives the
        *put_event* that is created at each put request and needs to decide if
        the request can be triggered or needs to enqueued. If the request can
        be triggered, it must also check if pending get requests can be
        triggered.
        """
        raise NotImplementedError(self)

    def _trigger_put(self, get_event):
        """Trigger pending put events after a get event has been executed."""
        if get_event is not None:
            self.get_queue.remove(get_event)

        for put_event in self.put_queue:
            if not put_event.triggered:
                self._do_put(put_event)
                if not put_event.triggered:
                    break

    def _do_get(self, event):
        """Perform the *get* operation.

        This methods needs to be implemented by subclasses. It receives the
        *get_event* that is created at each get request and needs to decide if
        the request can be triggered or needs to enqueued. If the request can
        be triggered, it must also check if pending put requests can be
        triggered.
        """
        raise NotImplementedError(self)

    def _trigger_get(self, put_event):
        """Trigger pending get events after a put event has been executed."""
        if put_event is not None:
            self.put_queue.remove(put_event)

        for get_event in self.get_queue:
            if not get_event.triggered:
                self._do_get(get_event)
                if not get_event.triggered:
                    break
