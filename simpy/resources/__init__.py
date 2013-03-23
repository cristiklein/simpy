from simpy.core import Event
from simpy.resources import queues
from collections import namedtuple


class BaseResource(object):
    def __init__(self, env, put_queue, get_queue, put_event,
            get_event):
        self._env = env
        self.put_event = put_event
        self.get_event = get_event
        self.put_queue = put_queue
        self.get_queue = get_queue

        self.request = self.put
        self.release = self.get

    def get(self, *args, **kwargs):
        get_event = self.get_event(self, *args, **kwargs)

        self._do_get(get_event)
        if get_event._triggered:
            # The get request has been added to the container and triggered.
            # Check if put requests may now be triggered.
            while self.put_queue:
                put_event = self.put_queue[0]
                self._do_put(put_event)
                if not put_event._triggered:
                    break

                self.put_queue.remove(put_event)
        else:
            self.get_queue.append(get_event)

        return get_event

    def put(self, *args, **kwargs):
        put_event = self.put_event(self, *args, **kwargs)

        self._do_put(put_event)
        if put_event._triggered:
            # The put request has been added to the container and triggered.
            # Check if get requests may now be triggered.
            while self.get_queue:
                get_event = self.get_queue[0]
                self._do_get(get_event)
                if not get_event._triggered:
                    break

                self.get_queue.remove(get_event)
        else:
            # The put request has not been added to the container.
            self.put_queue.append(put_event)

        return put_event

    def _do_put(self, event):
        raise NotImplementedError(self)

    def _do_get(self, event):
        raise NotImplementedError(self)


class Get(Event):
    def __init__(self, resource):
        Event.__init__(self, resource._env)
        self.resource = resource
        self.proc = self.env.active_process

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        # If the get request has been interrupted, remove it from the get
        # queue.
        if not self._triggered:
            self.resource.get_queue.remove(self)


class Put(Event):
    def __init__(self, resource):
        Event.__init__(self, resource._env)
        self.resource = resource
        self.proc = self.env.active_process

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        # If the put request has been interrupted, remove it from the put
        # queue.
        if not self._triggered:
            self.resource.put_queue.remove(self)


class Request(Put):
    def __exit__(self, exc_type, value, traceback):
        super(Request, self).__exit__(exc_type, value, traceback)
        self.resource.release(self)


class Release(Get):
    def __init__(self, resource, request):
        super(Release, self).__init__(resource)
        self.request = request


class Resource(BaseResource):
    def __init__(self, env, capacity=1):
        super(Resource, self).__init__(env, [], [], Request, Release)
        self._capacity = capacity
        self.users = []

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

    @property
    def capacity(self):
        return self._capacity

    @property
    def count(self):
        return len(self.users)

    def get_users(self):
        return [ev.proc for ev in self.users]

    def get_queued(self):
        return [ev.proc for ev in self.put_queue]


class PriorityResource(Resource):
    def __init__(self, env, capacity=1):
        super(PriorityResource, self).__init__(env, capacity)
        # FIXME Overriding queues and event types like this is a bit ugly.
        self.put_queue = SortedQueue()
        self.get_queue = SortedQueue()
        self.put_event = PriorityRequest


class PreemptiveResource(PriorityResource):
    def _do_put(self, event):
        if len(self.users) >= self.capacity and event.preempt:
            # Check if we can preempt another process
            preempt = sorted(self.users, key=lambda e: e.key)[-1]

            if preempt.key > event.key:
                self.users.remove(preempt)
                preempt.proc.interrupt(Preempted(by=event.proc,
                        usage_since=preempt.time))

        return super(PreemptiveResource, self)._do_put(event)


Preempted = namedtuple('Preempted', 'by, usage_since')
"""Used as interrupt cause for preempted processes."""


class PriorityRequest(Request):
    def __init__(self, resource, priority=0, preempt=True):
        super(PriorityRequest, self).__init__(resource)
        self.priority = priority
        self.preempt = preempt
        self.time = resource._env.now
        self.key = (self.priority, self.time)


class SortedQueue(list):
    def __init__(self, maxlen=None):
        super(SortedQueue, self).__init__()

    def append(self, item):
        super(SortedQueue, self).append(item)
        super(SortedQueue, self).sort(key=lambda e: e.key)


class StorePut(Put):
    def __init__(self, resource, item):
        super(StorePut, self).__init__(resource)
        self.item = item


class StoreGet(Get):
    pass


class Store(BaseResource):
    def __init__(self, env, capacity=1):
        super(Store, self).__init__(env, [], [], StorePut, StoreGet)
        self.capacity = capacity
        self.items = []

    def _do_put(self, event):
        if len(self.items) < self.capacity:
            self.items.append(event.item)
            event.succeed()

    def _do_get(self, event):
        if self.items:
            event.succeed(self.items.pop(0))


class ContainerPut(Put):
    def __init__(self, resource, amount):
        super(ContainerPut, self).__init__(resource)
        self.amount = amount


class ContainerGet(Get):
    def __init__(self, resource, amount):
        super(ContainerGet, self).__init__(resource)
        assert type(amount) == int
        self.amount = amount


class Container(BaseResource):
    def __init__(self, env, capacity, init=0):
        super(Container, self).__init__(env, [], [],
                ContainerPut, ContainerGet)

        self._capacity = capacity
        self._level = init

    def _do_put(self, event):
        if self._capacity - self._level >= event.amount:
            self._level += event.amount
            event.succeed()

    def _do_get(self, event):
        if self._level >= event.amount:
            self._level -= event.amount
            event.succeed()

    @property
    def capacity(self):
        return self._capacity

    @property
    def level(self):
        return self._level


class FilterStoreGet(StoreGet):
    def __init__(self, resource, filter=lambda items: True):
        super(FilterStoreGet, self).__init__(resource)
        self.filter = filter


class FilterQueue(list):
    def __init__(self, resource):
        super(FilterQueue, self).__init__()
        self.resource = resource

    def __getitem__(self, key):
        for event in self:
            if event.filter(self.resource.items):
                return event

    def __bool__(self):
        for event in self:
            if event.filter(self.resource.items):
                return True
        return False


class FilterStore(Store):
    def __init__(self, env, capacity=1):
        super(FilterStore, self).__init__(env, capacity)
        self.get_queue = FilterQueue(self)
        self.get_event = FilterStoreGet
