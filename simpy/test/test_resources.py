# encoding: utf-8
"""
Theses test cases demonstrate the API for shared resources.

"""
# Pytest gets the parameters "sim" and "log" from the *conftest.py* file
import pytest

import simpy


@pytest.mark.xfail
def test_resource(sim, log):
    """A *resource* is something with a limited numer of slots that need
    to be requested before and released after the usage (e.g., gas pumps
    at a gas station).

    """
    def pem(context, name, resource, log):
        yield resource.request(context)

        yield context.hold(1)
        resource.release(context)

        log.append((name, context.now))

    # *queue* parameter is optional, default: queue=FIFO()
    resource = simpy.Resource(slots=1, queue=simpy.FIFO())
    sim.start(pem, 'a', resource, log)
    sim.start(pem, 'b', resource, log)
    sim.simulate()

    assert log == [('a', 1), ('b',  2)]


@pytest.mark.xfail
def test_container(sim, log):
    """A *container* is a resource (of optinally limited capacity) where
    you can put in our take out a discrete or continuous amount of
    things (e.g., a box of lump sugar or a can of milk).  The *put* and
    *get* operations block if the buffer is to full or to empty. If they
    return, the process nows that the *put* or *get* operation was
    successfull.

    """
    def putter(context, buf, log):
        yield context.hold(1)
        while True:
            yield buf.put(2)
            log.append(('p', context.now))

    def getter(context, buf, log):
        yield buf.get(1)
        log.append(('g', context.now))

        yield context.hold(1)
        yield buf.get(1)
        log.append(('g', context.now))

    # All parameters are optional, default: init=0, capacity=inf,
    #                                       put_q=FIFO(), get_q=FIFO()
    buf = simpy.Buffer(init=0, capacity=2)
    sim.start(putter, buf, log)
    sim.start(getter, buf, log)
    sim.simulate(until=5)

    assert log == [('p', 1), ('g', 1), ('g', 2), ('p', 2)]


@pytest.mark.xfail
def test_store(sim):
    """A store offers items of various types (e.g., apples and pears).
    You put concrete objects into a store and will get a concrete object
    (in contrast to buffers, where you only now if the *put* or *get*
    operations were successfull but don’t get concrete objects).

    """
    def putter(context, store, item):
        yield store.put(item)

    def getter(context, store, itype, orig_item):
        item = yield store.get(itype)
        assert item is orig_item

    # All parameters are optinal, default: capacity=inf, put_q=FIFO(),
    #                                      get_q=FIFO()
    store = simpy.Store(capacity=2)
    item = object()

    # NOTE: Does the start order matter? Need to test this.
    sim.start(putter, store, item)
    sim.start(getter, store, object, item)
    sim.simulate()
