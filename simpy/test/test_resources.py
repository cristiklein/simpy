"""
Theses test cases demonstrate the API for shared resources.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import pytest

import simpy


#
# Tests for Resource
#


def test_resource(env, log):
    """A *resource* is something with a limited numer of slots that need
    to be requested before and released after the usage (e.g., gas pumps
    at a gas station).

    """
    def pem(env, name, resource, log):
        req = resource.request()
        yield req
        assert resource.count == 1

        yield env.timeout(1)
        resource.release(req)

        log.append((name, env.now))

    resource = simpy.Resource(env, capacity=1)
    assert resource.capacity == 1
    assert resource.count == 0
    env.process(pem(env, 'a', resource, log))
    env.process(pem(env, 'b', resource, log))
    env.run()

    assert log == [('a', 1), ('b',  2)]


def test_resource_context_manager(env, log):
    """The event that ``Resource.request()`` returns can be used as
    Context Manager."""
    def pem(env, name, resource, log):
        with resource.request() as request:
            yield request
            yield env.timeout(1)

        log.append((name, env.now))

    resource = simpy.Resource(env, capacity=1)
    env.process(pem(env, 'a', resource, log))
    env.process(pem(env, 'b', resource, log))
    env.run()

    assert log == [('a', 1), ('b',  2)]


def test_resource_slots(env, log):
    def pem(env, name, resource, log):
        with resource.request() as req:
            yield req
            log.append((name, env.now))
            yield env.timeout(1)

    resource = simpy.Resource(env, capacity=3)
    for i in range(9):
        env.process(pem(env, str(i), resource, log))
    env.run()

    assert log == [('0', 0), ('1', 0), ('2', 0), ('3', 1), ('4', 1), ('5', 1),
                   ('6', 2), ('7', 2), ('8', 2)]


def test_resource_continue_after_interrupt(env):
    """A process may be interrupted while waiting for a resource but
    should be able to continue waiting afterwards."""
    def pem(env, res):
        with res.request() as req:
            yield req
            yield env.timeout(1)

    def victim(env, res):
        try:
            evt = res.request()
            yield evt
            pytest.fail('Should not have gotten the resource.')
        except simpy.Interrupt:
            yield evt
            res.release(evt)
            assert env.now == 1

    def interruptor(env, proc):
        proc.interrupt()
        yield env.exit(0)

    res = simpy.Resource(env, 1)
    env.process(pem(env, res))
    proc = env.process(victim(env, res))
    env.process(interruptor(env, proc))
    env.run()


def test_resource_release_after_interrupt(env):
    """A process needs to release a resource, even it it was interrupted
    and does not continue to wait for it."""
    def blocker(env, res):
        with res.request() as req:
            yield req
            yield env.timeout(1)

    def victim(env, res):
        try:
            evt = res.request()
            yield evt
            pytest.fail('Should not have gotten the resource.')
        except simpy.Interrupt:
            # Dont wait for the resource
            res.release(evt)
            assert env.now == 0
            env.exit()

    def interruptor(env, proc):
        proc.interrupt()
        yield env.exit(0)

    res = simpy.Resource(env, 1)
    env.process(blocker(env, res))
    victim_proc = env.process(victim(env, res))
    env.process(interruptor(env, victim_proc))
    env.run()


def test_resource_cm_exception(env, log):
    """Resource with context manager receives an exception."""
    def process(env, resource, log, raise_):
        try:
            with resource.request() as req:
                yield req
                yield env.timeout(1)
                log.append(env.now)
                if raise_:
                    raise ValueError('Foo')
        except ValueError as err:
            assert err.args == ('Foo',)

    resource = simpy.Resource(env, 1)
    env.process(process(env, resource, log, True))
    # The second process is used to check if it was able to access the
    # resource:
    env.process(process(env, resource, log, False))
    env.run()

    assert log == [1, 2]


def test_resource_with_condition(env):
    def process(env, resource):
        with resource.request() as res_event:
            result = yield res_event | env.timeout(1)
            assert res_event in result

    resource = simpy.Resource(env, 1)
    env.process(process(env, resource))
    env.run()


def test_resource_with_priority_queue(env):
    def process(env, delay, resource, priority, res_time):
        yield env.timeout(delay)
        req = resource.request(priority=priority)
        yield req
        assert env.now == res_time
        yield env.timeout(5)
        resource.release(req)

    resource = simpy.PriorityResource(env, capacity=1)
    env.process(process(env, 0, resource, 2, 0))
    env.process(process(env, 2, resource, 3, 10))
    env.process(process(env, 2, resource, 3, 15))  # Test equal priority
    env.process(process(env, 4, resource, 1, 5))
    env.run()


def test_sorted_queue_maxlen(env):
    """Requests must fail if more than *maxlen* requests happen
    concurrently."""
    resource = simpy.PriorityResource(env, capacity=10)
    resource.put_queue.maxlen = 1

    def process(env, resource):
        resource.request(priority=1)
        try:
            resource.request(priority=1)
            pytest.fail('Expected a RuntimeError')
        except RuntimeError as e:
            assert e.args[0] == 'Cannot append event. Queue is full.'
        yield env.timeout(0)

    env.process(process(env, resource))
    env.run()


def test_get_users(env):
    def process(env, resource):
        with resource.request() as req:
            yield req
            yield env.timeout(1)

    resource = simpy.Resource(env, 1)
    procs = [env.process(process(env, resource)) for i in range(3)]
    env.run(until=1)
    assert [evt.proc for evt in resource.users] == procs[0:1]
    assert [evt.proc for evt in resource.queue] == procs[1:]

    env.run(until=2)
    assert [evt.proc for evt in resource.users] == procs[1:2]
    assert [evt.proc for evt in resource.queue] == procs[2:]


#
# Tests for PreemptiveResource
#


def test_preemptive_resource(env, log):
    def process(id, env, res, delay, prio, log):
        yield env.timeout(delay)
        with res.request(priority=prio) as req:
            try:
                yield req
                yield env.timeout(5)
                log.append((env.now, id))
            except simpy.Interrupt as ir:
                log.append((env.now, id, (ir.cause.by, ir.cause.usage_since)))

    res = simpy.PreemptiveResource(env, capacity=2)
    env.process(process(0, env, res, 0, 1, log))
    env.process(process(1, env, res, 0, 1, log))
    p2 = env.process(process(2, env, res, 1, 0, log))
    env.process(process(3, env, res, 2, 2, log))

    env.run()

    assert log == [(1, 1, (p2, 0)), (5, 0), (6, 2), (10, 3)]


def test_preemptive_resource_timeout_0(env):
    def proc_a(env, resource, prio):
        with resource.request(priority=prio) as req:
            try:
                yield req
                yield env.timeout(1)
                pytest.fail('Should have received an interrupt/preemption.')
            except simpy.Interrupt:
                pass
        yield env.event()

    def proc_b(env, resource, prio):
        with resource.request(priority=prio) as req:
            yield req

    resource = simpy.PreemptiveResource(env, 1)
    env.process(proc_a(env, resource, 1))
    env.process(proc_b(env, resource, 0))

    env.run()


def test_mixed_preemption(env, log):
    def process(id, env, res, delay, prio, preempt, log):
        yield env.timeout(delay)
        with res.request(priority=prio, preempt=preempt) as req:
            try:
                yield req
                yield env.timeout(5)
                log.append((env.now, id))
            except simpy.Interrupt as ir:
                log.append((env.now, id, (ir.cause.by, ir.cause.usage_since)))

    res = simpy.PreemptiveResource(env, 2)
    env.process(process(0, env, res, 0, 1, True, log))
    env.process(process(1, env, res, 0, 1, True, log))
    env.process(process(2, env, res, 1, 0, False, log))
    p3 = env.process(process(3, env, res, 1, 0, True, log))
    env.process(process(4, env, res, 2, 2, True, log))

    env.run()

    assert log == [(1, 1, (p3, 0)), (5, 0), (6, 3), (10, 2), (11, 4)]

#
# Tests for Container
#


def test_container(env, log):
    """A *container* is a resource (of optinally limited capacity) where
    you can put in our take out a discrete or continuous amount of
    things (e.g., a box of lump sugar or a can of milk).  The *put* and
    *get* operations block if the buffer is to full or to empty. If they
    return, the process nows that the *put* or *get* operation was
    successfull.

    """
    def putter(env, buf, log):
        yield env.timeout(1)
        while True:
            yield buf.put(2)
            log.append(('p', env.now))
            yield env.timeout(1)

    def getter(env, buf, log):
        yield buf.get(1)
        log.append(('g', env.now))

        yield env.timeout(1)
        yield buf.get(1)
        log.append(('g', env.now))

    buf = simpy.Container(env, init=0, capacity=2)
    env.process(putter(env, buf, log))
    env.process(getter(env, buf, log))
    env.run(until=5)

    assert log == [('p', 1), ('g', 1), ('g', 2), ('p', 2)]


def test_container_get_queued(env):
    def proc(env, wait, container, what):
        yield env.timeout(wait)
        with getattr(container, what)(1) as req:
            yield req

    container = simpy.Container(env, 1)
    p0 = env.process(proc(env, 0, container, 'get'))
    env.process(proc(env, 1, container, 'put'))
    env.process(proc(env, 1, container, 'put'))
    p3 = env.process(proc(env, 1, container, 'put'))

    env.run(until=1)
    assert [ev.proc for ev in container.put_queue] == []
    assert [ev.proc for ev in container.get_queue] == [p0]

    env.run(until=2)
    assert [ev.proc for ev in container.put_queue] == [p3]
    assert [ev.proc for ev in container.get_queue] == []


def test_initial_container_capacity(env):
    container = simpy.Container(env)
    assert container.capacity == float('inf')


@pytest.mark.parametrize(('error', 'args'), [
    (None, [2, 1]),  # normal case
    (None, [1, 1]),  # init == capacity should be valid
    (None, [1, 0]),  # init == 0 should be valid
    (ValueError, [1, 2]),  # init > capcity
    (ValueError, [0]),  # capacity == 0
    (ValueError, [-1]),  # capacity < 0
    (ValueError, [1, -1]),  # init < 0
])
def test_container_init_capacity(env, error, args):
    args.insert(0, env)
    if error:
        pytest.raises(error, simpy.Container, *args)
    else:
        simpy.Container(*args)


#
# Tests fore Store
#


def test_store(env):
    """A store models the production and consumption of concrete python
    objects (in contrast to containers, where you only now if the *put*
    or *get* operations were successfull but don't get concrete
    objects).

    """
    def putter(env, store, item):
        yield store.put(item)

    def getter(env, store, orig_item):
        item = yield store.get()
        assert item is orig_item

    store = simpy.Store(env, capacity=2)
    item = object()

    # NOTE: Does the start order matter? Need to test this.
    env.process(putter(env, store, item))
    env.process(getter(env, store, item))
    env.run()


@pytest.mark.parametrize('Store', [
    simpy.Store,
    simpy.FilterStore,
])
def test_initial_store_capacity(env, Store):
    store = Store(env)
    assert store.capacity == float('inf')


def test_store_capacity(env):
    simpy.Store(env, 1)
    pytest.raises(ValueError, simpy.Store, env, 0)
    pytest.raises(ValueError, simpy.Store, env, -1)


def test_filter_store(env):
    def pem(env):
        store = simpy.FilterStore(env, capacity=2)

        get_event = store.get(lambda item: item == 'b')
        yield store.put('a')
        assert not get_event.triggered
        yield store.put('b')
        assert get_event.triggered

    env.process(pem(env))
    env.run()
