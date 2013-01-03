"""
Theses test cases demonstrate the API for shared resources.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import pytest

import simpy


#
# Tests fore Resource
#


def test_resource(env, log):
    """A *resource* is something with a limited numer of slots that need
    to be requested before and released after the usage (e.g., gas pumps
    at a gas station).

    """
    def pem(env, name, resource, log):
        yield resource.request()

        yield env.timeout(1)
        resource.release()

        log.append((name, env.now))

    # *queue* parameter is optional, default: queue=FIFO()
    resource = simpy.Resource(env, capacity=1, queue=simpy.FIFO())
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

    # *queue* parameter is optional, default: queue=FIFO()
    resource = simpy.Resource(env, capacity=1, queue=simpy.FIFO())
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
        yield res.request()
        yield env.timeout(1)
        res.release()

    def victim(env, res):
        try:
            evt = res.request()
            yield evt
            pytest.fail('Should not have gotten the resource.')
        except simpy.Interrupt:
            yield evt
            res.release()
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
        yield res.request()
        yield env.timeout(1)
        res.release()

    def victim(env, res):
        try:
            evt = res.request()
            yield evt
            pytest.fail('Should not have gotten the resource.')
        except simpy.Interrupt:
            # Dont wait for the resource
            res.release()
            assert env.now == 0
            env.exit()

    def interruptor(env, proc):
        proc.interrupt()
        yield env.exit(0)

    res = simpy.Resource(env, 1)
    env.start(pem(env, res))
    proc = env.start(victim(env, res))
    env.start(interruptor(env, proc))
    env.start(pem(env, res))
    simpy.simulate(env)


def test_resource_illegal_release(env):
    """A process must be either waiting for or using a resource in order
    to release it."""
    def pem(env, res):
        res.release()
        yield

    res = simpy.Resource(env, 1)
    env.start(pem(env, res))
    with pytest.raises(ValueError) as excinfo:
        simpy.simulate(env)
    assert excinfo.value.args[0].startswith('Cannot release resource')


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
    env.start(process(env, resource, log, False))
    simpy.simulate(env)

    assert log == [1, 2]


def test_resource_with_condition(env):
    def process(env, resource):
        res_event = resource.request()
        result = yield res_event | env.timeout(1)
        assert res_event in result
        resource.release()

    resource = simpy.Resource(env, 1)
    env.start(process(env, resource))
    env.start(process(env, resource))
    simpy.simulate(env)


def test_resource_with_lifo_queue(env):
    def process(env, delay, resource, res_time):
        yield env.timeout(delay)
        yield resource.request()
        assert env.now == res_time
        yield env.timeout(5)
        resource.release()

    resource = simpy.Resource(env, capacity=1, queue=simpy.LIFO())
    env.start(process(env, 0, resource, 0))
    env.start(process(env, 2, resource, 10))
    env.start(process(env, 4, resource, 5))
    simpy.simulate(env)


def test_resource_with_priority_queue(env):
    def process(env, delay, resource, priority, res_time):
        yield env.timeout(delay)
        yield resource.request(priority=priority)
        assert env.now == res_time
        yield env.timeout(5)
        resource.release()

    resource = simpy.Resource(env, capacity=1, queue=simpy.Priority())
    env.start(process(env, 0, resource, 1, 0))
    env.start(process(env, 2, resource, 4, 10))
    env.start(process(env, 4, resource, 2, 5))
    simpy.simulate(env)


#
# Tests for Container
#
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

    # All parameters are optional, default: init=0, capacity=inf,
    #                                       put_q=FIFO(), get_q=FIFO()
    buf = simpy.Container(env, init=0, capacity=2)
    env.start(putter(env, buf, log))
    env.start(getter(env, buf, log))
    simpy.simulate(env, until=5)

    assert log == [('g', 1), ('p', 1), ('g', 2), ('p', 2)]


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

    # All parameters are optinal, default: capacity=inf, put_q=FIFO(),
    #                                      get_q=FIFO(), item_q=FIFO()
    store = simpy.Store(env, capacity=2)
    item = object()

    # NOTE: Does the start order matter? Need to test this.
    env.start(putter(env, store, item))
    env.start(getter(env, store, item))
    simpy.simulate(env)
