"""
This module contains the base classes for Simpy's resource system.

:class:`BaseResource` defines the abstract base resource. The request for
putting something into or getting something out of a resource is modeled as an
event that has to be yielded by the requesting process. :class:`Put` and
:class:`Get` are the base event types for this.

"""
from simpy.core import BoundClass
from simpy.events import Event


class Put(Event):
    """The base class for all put events.

    It receives the *resource* that created the event.

    This event (and all of its subclasses) can act as context manager and can
    be used with the :keyword:`with` statement to automatically cancel a put
    request if an exception or an :class:`simpy.events.Interrupt` occurs:

    .. code-block:: python

        with res.put(item) as request:
            yield request

    It is not used directly by any resource, but rather sub-classed for each
    type.

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
        # If the request has been interrupted, remove it from the queue:
        if not self.triggered:
            self.resource.put_queue.remove(self)

    cancel = __exit__
    """Cancel the current put request.

    This method has to be called if a process received an
    :class:`~simpy.events.Interrupt` or an exception while yielding this event
    and is not going to yield this event again.

    If the event was created in a :keyword:`with` statement, this method is
    called automatically.

    """


class Get(Event):
    """The base class for all get events.

    It receives the *resource* that created the event.

    This event (and all of its subclasses) can act as context manager and can
    be used with the :keyword:`with` statement to automatically cancel a get
    request if an exception or an :class:`simpy.events.Interrupt` occurs:

    .. code-block:: python

        with res.get() as request:
            yield request

    It is not used directly by any resource, but rather sub-classed for each
    type.

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
        # If the request has been interrupted, remove it from the queue:
        if not self.triggered:
            self.resource.get_queue.remove(self)

    cancel = __exit__
    """Cancel the current get request.

    This method has to be called if a process received an
    :class:`~simpy.events.Interrupt` or an exception while yielding this event
    and is not going to yield this event again.

    If the event was created in a :keyword:`with` statement, this method is
    called automatically.

    """


class BaseResource(object):
    """This is the abstract base class for all SimPy resources.

    All resources are bound to a specific :class:`~simpy.core.Environment`
    *env*.

    You can :meth:`put()` something into the resources or :meth:`get()`
    something out of it. Both methods return an event that the requesting
    process has to ``yield``.

    If a put or get operation can be performed immediately (because the
    resource is not full (put) or not empty (get)), that event is triggered
    immediately.

    If a resources is too full or too empty to perform a put or get request,
    the event is pushed to the *put_queue* or *get_queue*. An event is popped
    from one of these queues and triggered as soon as the corresponding
    operation is possible.

    :meth:`put()` and :meth:`get()` only provide the user API and the general
    framework and should not be overridden in subclasses. The actual behavior
    for what happens when a put/get succeeds should rather be implemented in
    :meth:`_do_put()` and :meth:`_do_get()`.

    """

    PutQueue = list
    """The type to be used for the :attr:`put_queue`. This can either be
    a plain :class:`list` (default) or a subclass of it."""

    GetQueue = list
    """The type to be used for the :attr:`get_queue`. This can either be
    a plain :class:`list` (default) or a subclass of it."""

    def __init__(self, env):
        self._env = env
        self.put_queue = self.PutQueue()
        """Queue/list of events waiting to get something out of the resource.
        """
        self.get_queue = self.GetQueue()
        """Queue/list of events waiting to put something into the resource."""

        # Bind event constructors as methods
        BoundClass.bind_early(self)

    put = BoundClass(Put)
    """Create a new :class:`Put` event."""

    get = BoundClass(Get)
    """Create a new :class:`Get` event."""

    def _do_put(self, event):
        """Actually perform the *put* operation.

        This methods needs to be implemented by subclasses. It receives the
        *put_event* that is created at each request and doesn't need to return
        anything.

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
        """Actually perform the *get* operation.

        This methods needs to be implemented by subclasses. It receives the
        *get_event* that is created at each request and doesn't need to return
        anything.

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
