"""
Theses test cases demonstrate the API for shared resources.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import simpy

# TODO:
# request() not yielded
# Interrupt during request(), cancel waiting
# Interrupt during request(), continue waiting
# Container.level
# Store.count


def test_resource(env, log):
    """A *resource* is something with a limited numer of slots that need
    to be requested before and released after the usage (e.g., gas pumps
    at a gas station).

    """
    def pem(env, name, resource, log):
        yield resource.request()

        yield env.hold(1)
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
        yield env.hold(1)
        resource.release()

    resource = simpy.Resource(env, capacity=3)
    for i in range(9):
        env.start(pem(env, str(i), resource, log))
    simpy.simulate(env)

    assert log == [('0', 0), ('1', 0), ('2', 0),
            ('3', 1), ('4', 1), ('5', 1),
            ('6', 2), ('7', 2), ('8', 2),
    ]


def test_container(env, log):
    """A *container* is a resource (of optinally limited capacity) where
    you can put in our take out a discrete or continuous amount of
    things (e.g., a box of lump sugar or a can of milk).  The *put* and
    *get* operations block if the buffer is to full or to empty. If they
    return, the process nows that the *put* or *get* operation was
    successfull.

    """
    def putter(env, buf, log):
        yield env.hold(1)
        while True:
            yield buf.put(2)
            log.append(('p', env.now))
            yield env.hold(1)

    def getter(env, buf, log):
        yield buf.get(1)
        log.append(('g', env.now))

        yield env.hold(1)
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
