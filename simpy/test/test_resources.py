"""
Theses test cases demonstrate the API for shared resources.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import pytest

import simpy


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


def test_resource_slots(env, log):
    def pem(env, name, resource, log):
        yield resource.request()
        log.append((name, env.now))
        yield env.timeout(1)
        resource.release()

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
        try:
            evt = res.request()
            yield evt
            pytest.fail('Should not have gotten the resource.')
        except simpy.Interrupt:
            yield evt
            res.release()
            assert env.now == 0

    def interruptor(env, proc):
        proc.interrupt()
        env.exit(0)
        yield

    res = simpy.Resource(env, 1)
    proc = env.start(pem(env, res))
    env.start(interruptor(env, proc))
    simpy.simulate(env)


def test_resource_release_after_interrupt(env):
    """A process needs to release a resource, even it it was interrupted
    and does not continue to wait for it."""
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

    def pem(env, res):
        yield res.request()
        assert env.now == 0
        res.release()

    def interruptor(env, proc):
        proc.interrupt()
        env.exit(0)
        yield

    res = simpy.Resource(env, 1)
    victim_proc = env.start(victim(env, res))
    env.start(interruptor(env, victim_proc))
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


def test_resource_not_released(env):
    """An error should be thrown if the resource detects that a process
    didn't release it."""
    def pem(env, res):
        yield res.request()
        res.release()

    def evil_knievel(env, res):
        try:
            yield res.request()
        except simpy.Interrupt:
            pass  # Onoes, resource no can haz release!

    res = simpy.Resource(env, 1)
    env.start(pem(env, res))
    ek = env.start(evil_knievel(env, res))
    ek.interrupt()
    with pytest.raises(RuntimeError) as excinfo:
        simpy.simulate(env)
    assert excinfo.value.args[0] == ('Process(evil_knievel) did not release '
                                     'the resource.')


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
