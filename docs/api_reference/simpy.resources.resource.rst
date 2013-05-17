=======================================================
``simpy.resources.resource`` -- Resource type resources
=======================================================

.. automodule:: simpy.resources.resource

.. autoclass:: Resource

    .. attribute:: users

        List of :class:`Request` events for the processes that are
        currently using the resource.

    .. attribute:: queue

        Queue/list of pending :class:`Request` events that represent
        processes waiting to use the resource.

    .. autoattribute:: capacity
    .. autoattribute:: count

    .. method:: request()

        Create a new :class:`Request` event.

    .. method:: release()

        Create a new :class:`Release` event.

.. autoclass:: PriorityResource

    .. method:: request(priority=0)

        Create a new :class:`PriorityRequest` event.


.. autoclass:: PreemptiveResource

.. autoclass:: Preempted(by, usage_since)

.. autoclass:: Request

.. autoclass:: Release

    .. attribute:: request

        The request (:class:`Request`) that is to be released.

.. autoclass:: PriorityRequest

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

.. autoclass:: SortedQueue


