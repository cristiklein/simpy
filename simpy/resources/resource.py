"""
This module contains all :class:`Resource` like resources.

These resources can be used by a limited number of processes at a time
(e.g., a gas station with a limited number of fuel pumps). Processes
*request* these resources to become a user (or to own them) and have to
*release* them once they are done (e.g., vehicles arrive at the gas
station, use a fuel-pump, if one is availalbe, and leave when they are
done).

Requesting a resources is modeled as "putting a process' token into the
resources" and releasing a resources correspondingly as "getting
a process' token out of the resource". Thus, calling
``request()``/``release()`` is equivalent to calling
``put()``/``get()``. Note, that releasing a resource will always succeed
immediately, no matter if a process is actually using a resource or not.

Beside :class:`Resource`, there are a :class:`PriorityResource`, were
processes can define a request priority, and
a :class:`PreemptiveResource` were resource users can be preempted by
other processes with a higher priority.

.. autoclass:: Resource
.. autoclass:: PriorityResource
.. autoclass:: PreemptiveResource
.. autoclass:: Preempted(by, usage_since)
.. autoclass:: Request
.. autoclass:: Release
.. autoclass:: PriorityRequest
.. autoclass:: SortedQueue


"""
from collections import namedtuple

from simpy.resources import base


Preempted = namedtuple('Preempted', 'by, usage_since')
"""Used as interrupt cause for preempted processes.

.. attribute:: by

    The preempting process

.. attribute:: usage_since

    The simulation time at which the preempted process started to use
    the resource.

"""


class Request(base.Put):
    """This event type is used by :meth:`Resource.request()`.

    It automatically calls :meth:`Resource.release()` when the request
    was created within a :keyword:`with` statement.

    """
    def __exit__(self, exc_type, value, traceback):
        super(Request, self).__exit__(exc_type, value, traceback)
        self.resource.release(self)


class Release(base.Get):
    """This event type is used by :meth:`Resource.release()`.

    .. attribute:: request

        The request (:class:`Request`) that is to be released.

    """
    def __init__(self, resource, request):
        super(Release, self).__init__(resource)
        self.request = request


class PriorityRequest(Request):
    """This event type inherits :class:`Request` and adds some
    additional attributes needed by :class:`PriorityResource` and
    :class:`PreemptiveResource`

    .. attribute:: priority

        The priority of this request. A smaller number means higher
        priority.

    .. attribute:: preempt

        Indicates wether the request should preempt a resource user or
        not (this flag is not taken into account by
        :class:`PriorityResource`).

    .. attribute:: time

        The simulation time at which the request was made.

    .. attribute:: key

        Key for sorting events. Consists of the priority (lower value is
        more important) and the time at witch the request was made
        (earlier requests are more important).

    """
    def __init__(self, resource, priority=0, preempt=True):
        super(PriorityRequest, self).__init__(resource)
        self.priority = priority
        self.preempt = preempt
        self.time = resource._env.now
        self.key = (self.priority, self.time)


class SortedQueue(list):
    """Queue that sorts events by their ``key`` attribute."""
    def __init__(self, maxlen=None):
        super(SortedQueue, self).__init__()
        self.maxlen = maxlen

    def append(self, item):
        if self.maxlen is not None and len(self) >= self.maxlen:
            raise ValueError('Cannot append event. Queue is full.')

        super(SortedQueue, self).append(item)
        super(SortedQueue, self).sort(key=lambda e: e.key)


class Resource(base.BaseResource):
    """A resource has a limited number of slots that can be requested
    by a process.

    If all slots are taken, requesters are put into a queue. If
    a process releases a slot, the next process is popped from the queue
    and gets one slot.

    The ``env`` parameter is the :class:`~simpy.core.Environment`
    instance the resource is bound to.

    The ``capacity`` defines the number of slots and must be a positive
    integer.


    .. attribute:: users

        List of :class:`Request` events for the processes that are
        currently using the resource.

    .. attribute:: queue

        Queue/list of pending :class:`Request` events that represent
        processes waiting to use the resource.

    .. autoattribute:: capacity
    .. autoattribute:: count

    .. method:: request()

        Request the resource.

        If the maximum capacity of users is not reached, the requesting
        process obtains the resource immediately (that is, a new event
        for it will be scheduled at the current time. That means that
        all other events also scheduled for the current time will be
        processed before that new event.).

        If the maximum capacity is reached, suspend the requesting
        process until another process releases the resource again.

    .. method:: release()

        Release the resource for the process that created event.

        If another process is waiting for the resource, resume that
        process.

        If the request was made after a :keyword:`with` statement (e.g.,
        ``with res.request() as req:``), this method is automatically
        called when the ``with`` block is left.

    """
    PutEvent = Request
    GetEvent = Release
    request = base.BaseResource.put
    release = base.BaseResource.get

    def __init__(self, env, capacity=1):
        super(Resource, self).__init__(env)
        self._capacity = capacity
        self.users = []
        self.queue = self.put_queue

    @property
    def capacity(self):
        """Maximum capacity of the resource."""
        return self._capacity

    @property
    def count(self):
        """Number of users currently using the resource."""
        return len(self.users)

    def _do_put(self, event):
        if len(self.users) < self.capacity:
            self.users.append(event)
            event.succeed()

    def _do_get(self, event):
        try:
            self.users.remove(event.request)
        except ValueError:
            pass
        event.succeed()


class PriorityResource(Resource):
    """This class works like :class:`Resource`, but waiting processes
    are sorted by priority (see :meth:`request()`).

    .. method:: request(priority=0)

        Request the resource with a given *priority*.

        This method has the same behavior as :meth:`Resource.request()`,
        but the :attr:`~Resource.queue` is kept sorted by priority in
        ascending order (a lower value for *priority* results in
        a higher priority), so more important processes will get the
        resource earlier.

    """
    PutEvent = PriorityRequest
    PutQueue = SortedQueue
    GetQueue = SortedQueue


class PreemptiveResource(PriorityResource):
    """This resource mostly works like :class:`Resource`, but users of
    the resource can be *preempted* by higher prioritized processes.

    Furthermore, the queue for waiting requests is also sorted by
    *priority*.

    .. method:: request(priority=0, preempt=True)

        Request the resource with a given *priority* and preempt less
        important resource users if *preempt* is ``True``.

        This method has the same behavior as :meth:`Resource.request()`,
        but the :attr:`~Resource.queue` is kept sorted by priority in
        ascending order (a lower value for *priority* results in
        a higher priority), so more important processes will get the
        resource earlier.

        If a less important process is preempted, it will receive an
        :class:`~simpy.core.Interrupt` with a :class:`Preempted`
        instance as cause.

    """
    def _do_put(self, event):
        if len(self.users) >= self.capacity and event.preempt:
            # Check if we can preempt another process
            preempt = sorted(self.users, key=lambda e: e.key)[-1]

            if preempt.key > event.key:
                self.users.remove(preempt)
                preempt.proc.interrupt(Preempted(by=event.proc,
                                                 usage_since=preempt.time))

        return super(PreemptiveResource, self)._do_put(event)
