"""
Performance benchmark tests using the `pytest-benchmark` package.

Benchmarks are divided into three groups: *frequent*, *targeted*, and
*simulation*. The *frequent* group benchmarks various simpy functions expected
to be called frequently in normal simulations. The *targeted* group benchmarks
singular behaviors run by the environment. The *simulation* group benchmarks
complete simulations using processes and resources.

"""
import random

import pytest
import simpy


@pytest.mark.benchmark(group='frequent')
def test_event_init(env, benchmark):
    benchmark(env.event)


@pytest.mark.benchmark(group='frequent')
def test_timeout_init(env, benchmark):
    benchmark(env.timeout, 1)


@pytest.mark.benchmark(group='frequent')
def test_process_init(env, benchmark):
    def g():
        yield env.timeout(1)

    benchmark(env.process, g())


@pytest.mark.benchmark(group='frequent')
def test_environment_step(env, benchmark):
    def g(env):
        while True:
            yield env.timeout(1)

    env.process(g(env))
    benchmark(env.step)


@pytest.mark.benchmark(group='targeted')
def test_condition_events(env, benchmark):
    def cond_proc(env):
        yield (env.timeout(0) & (env.timeout(2) | env.timeout(1)))

    def sim():
        for _ in range(20):
            env.process(cond_proc(env))
        env.run()

    benchmark(sim)


@pytest.mark.benchmark(group='targeted')
def test_condition_wait(env, benchmark):
    def cond_proc(env):
        yield env.all_of(env.timeout(i) for i in range(10))

    def sim():
        for _ in range(10):
            env.process(cond_proc(env))
        env.run()

    benchmark(sim)


@pytest.mark.benchmark(group='targeted')
def test_wait_for_proc(env, benchmark):
    r = random.Random(1234)

    def child(env):
        yield env.timeout(r.randint(1, 1000))

    def parent(env):
        children = [env.process(child(env)) for _ in range(10)]
        for proc in children:
            if not proc.triggered:
                yield proc

    def sim(env):
        for _ in range(5):
            env.process(parent(env))
        env.run()

    benchmark(sim, env)


@pytest.mark.benchmark(group='simulation')
def test_store_sim(benchmark):
    def producer(env, store, n):
        for i in range(n):
            yield env.timeout(1)
            yield store.put(i)

    def consumer(env, store):
        while True:
            yield store.get()
            yield env.timeout(2)

    def sim():
        env = simpy.Environment()
        store = simpy.Store(env, capacity=5)
        for _ in range(2):
            env.process(producer(env, store, 10))
        for _ in range(3):
            env.process(consumer(env, store))
        env.run()
        return next(env._eid)

    num_events = benchmark(sim)
    assert num_events == 87


@pytest.mark.benchmark(group='simulation')
def test_resource_sim(benchmark):
    def worker(env, resource):
        while True:
            with resource.request() as req:
                yield req
                yield env.timeout(1)

    def sim():
        env = simpy.Environment()
        resource = simpy.Resource(env, capacity=2)
        for _ in range(5):
            env.process(worker(env, resource))
        env.run(until=15)
        return next(env._eid)

    num_events = benchmark(sim)
    assert num_events == 94


@pytest.mark.benchmark(group='simulation')
def test_container_sim(benchmark):
    def producer(env, container, full_event):
        while True:
            yield container.put(1)
            if container.level == container.capacity:
                full_event.succeed()
            yield env.timeout(1)

    def consumer(env, container):
        while True:
            yield container.get(1)
            yield env.timeout(3)

    def sim():
        env = simpy.Environment()
        container = simpy.Container(env, capacity=10)
        full_event = env.event()
        env.process(producer(env, container, full_event))
        for _ in range(2):
            env.process(consumer(env, container))
        env.run(until=full_event)
        return next(env._eid)

    num_events = benchmark(sim)
    assert num_events == 104
