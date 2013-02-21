"""
Theses test cases demonstrate the API for shared resources.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import pytest

import simpy
import simpy.resources


#
# Tests fore Resource
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
    env.start(pem(env, 'a', resource, log))
    env.start(pem(env, 'b', resource, log))
    simpy.simulate(env)

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
    env.start(pem(env, 'a', resource, log))
    env.start(pem(env, 'b', resource, log))
    simpy.simulate(env)

    assert log == [('a', 1), ('b',  2)]


def test_resource_slots(env, log):
    def pem(env, name, resource, log):
        with resource.request() as req:
            yield req
            log.append((name, env.now))
            yield env.timeout(1)

    resource = simpy.Resource(env, capacity=3)
    for i in range(9):
        env.start(pem(env, str(i), resource, log))
    simpy.simulate(env)

    assert log == [('0', 0), ('1', 0), ('2', 0),
            ('3', 1), ('4', 1), ('5', 1),
            ('6', 2), ('7', 2), ('8', 2),
    ]


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
    env.start(pem(env, res))
    proc = env.start(victim(env, res))
    env.start(interruptor(env, proc))
    simpy.simulate(env)


def test_resource_release_after_interrupt(env):
    """A process needs to release a resource, even it it was interrupted
    and does not continue to wait for it."""
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
            # Dont wait for the resource
            res.release(evt)
            assert env.now == 0
            env.exit()

    def interruptor(env, proc):
        proc.interrupt()
        yield env.exit(0)

    res = simpy.Resource(env, 1)
    victim_proc = env.start(victim(env, res))
    env.start(interruptor(env, victim_proc))
    env.start(pem(env, res))
    simpy.simulate(env)


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
    env.start(process(env, resource, log, True))
    # The second process is used to check if it was able to access the
    # resource:
    env.start(process(env, resource, log, False))
    simpy.simulate(env)

    assert log == [1, 2]


def test_resource_with_condition(env):
    def process(env, resource):
        with resource.request() as res_event:
            result = yield res_event | env.timeout(1)
            assert res_event in result

    resource = simpy.Resource(env, 1)
    env.start(process(env, resource))
    simpy.simulate(env)


def test_resource_with_priority_queue(env):
    def process(env, delay, resource, priority, res_time):
        yield env.timeout(delay)
        req = resource.request(priority=priority)
        yield req
        assert env.now == res_time
        yield env.timeout(5)
        resource.release(req)

    resource = simpy.Resource(env, capacity=1,
                    event_type=simpy.resources.events.PriorityResourceEvent)
    env.start(process(env, 0, resource, 2, 0))
    env.start(process(env, 2, resource, 3, 10))
    env.start(process(env, 2, resource, 3, 15))  # Test equal priority
    env.start(process(env, 4, resource, 1, 5))
    simpy.simulate(env)


def test_get_users(env):
    def process(env, resource):
        with resource.request() as req:
            yield req
            yield env.timeout(1)

    resource = simpy.Resource(env, 1)
    procs = [env.start(process(env, resource)) for i in range(3)]
    simpy.simulate(env, until=1)
    assert resource.get_users() == procs[0:1]
    assert resource.get_queued() == procs[1:]

    simpy.simulate(env, until=2)
    assert resource.get_users() == procs[1:2]
    assert resource.get_queued() == procs[2:]


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
                log.append((env.now, id, tuple(ir.cause)))

    res = simpy.PreemptiveResource(env, 2)
    p0 = env.start(process(0, env, res, 0, 1, log))
    p1 = env.start(process(1, env, res, 0, 1, log))
    p2 = env.start(process(2, env, res, 1, 0, log))
    p3 = env.start(process(3, env, res, 2, 2, log))

    simpy.simulate(env)

    assert log == [(1, 1, (p2, 0)), (5, 0), (6, 2), (10, 3)]


def test_preemptive_resource_timeout_0(env):
    def proc_a(env, resource, prio):
        with resource.request(priority=prio) as req:
            yield req
            try:
                yield env.timeout(0)
                pytest.fail('Should have received an interrupt/preemption.')
            except simpy.Interrupt:
                pass
        yield env.event()

    def proc_b(env, resource, prio):
        yield env.timeout(0)
        with resource.request(priority=prio) as req:
            yield req

    resource = simpy.PreemptiveResource(env, 1)
    env.start(proc_a(env, resource, 1))
    env.start(proc_b(env, resource, 0))

    simpy.simulate(env)


def test_mixed_preemption(env, log):
    def process(id, env, res, delay, prio, preempt, log):
        yield env.timeout(delay)
        with res.request(priority=prio, preempt=preempt) as req:
            try:
                yield req
                yield env.timeout(5)
                log.append((env.now, id))
            except simpy.Interrupt as ir:
                log.append((env.now, id, tuple(ir.cause)))

    res = simpy.PreemptiveResource(env, 2)
    p0 = env.start(process(0, env, res, 0, 1, True, log))
    p1 = env.start(process(1, env, res, 0, 1, True, log))
    p2 = env.start(process(2, env, res, 1, 0, False, log))
    p3 = env.start(process(3, env, res, 1, 0, True, log))
    p4 = env.start(process(4, env, res, 2, 2, True, log))

    simpy.simulate(env)

    assert log == [
        (1, 1, (p3, 0)),
        (5, 0),
        (6, 3),
        (10, 2),
        (11, 4),
    ]

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
    env.start(putter(env, buf, log))
    env.start(getter(env, buf, log))
    simpy.simulate(env, until=5)

    assert log == [('g', 1), ('p', 1), ('g', 2), ('p', 2)]


def test_container_get_queued(env):
    def proc(env, wait, container, what):
        yield env.timeout(wait)
        with getattr(container, what)(1) as req:
            print(env.now, what, container.level)
            yield req

    container = simpy.Container(env, 1)
    p0 = env.start(proc(env, 0, container, 'get'))
    p1 = env.start(proc(env, 1, container, 'put'))
    p2 = env.start(proc(env, 1, container, 'put'))
    p3 = env.start(proc(env, 1, container, 'put'))

    simpy.simulate(env, until=1)
    print('simulated')
    assert container.get_put_queued() == []
    assert container.get_get_queued() == [p0]

    simpy.simulate(env, until=2)
    print('simulated')
    assert container.get_put_queued() == [p3]
    assert container.get_get_queued() == []


#
# Tests fore Store
#


def test_store(env):
    """A store models the production and consumption of concrete python
    objects (in contrast to containers, where you only now if the *put*
    or *get* operations were successfull but don’t get concrete
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
    env.start(putter(env, store, item))
    env.start(getter(env, store, item))
    simpy.simulate(env)
