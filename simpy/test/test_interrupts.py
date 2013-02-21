"""
Test asynchronous interrupts.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import pytest

import simpy


def test_interruption(env):
    """With asynchronous interrupts, the victim expects an interrupt
    while waiting for an event, but will process this even if no
    interrupt occurred.

    """
    def interruptee(env):
        try:
            yield env.timeout(10)
            pytest.fail('Expected an interrupt')
        except simpy.Interrupt as interrupt:
            assert interrupt.cause == 'interrupt!'

    def interruptor(env):
        child_process = env.start(interruptee(env))
        yield env.timeout(5)
        child_process.interrupt('interrupt!')

    env.start(interruptor(env))
    simpy.simulate(env)


def test_concurrent_interrupts(env, log):
    """Concurrent interrupts are scheduled in the order in which they
    occurred.

    """
    def fox(env, log):
        while True:
            try:
                yield env.timeout(10)
            except simpy.Interrupt as interrupt:
                log.append((env.now, interrupt.cause))

    def farmer(env, name, fox):
        fox.interrupt(name)
        yield env.timeout(1)

    fantastic_mr_fox = env.start(fox(env, log))
    for name in ('boggis', 'bunce', 'beans'):
        env.start(farmer(env, name, fantastic_mr_fox))

    simpy.simulate(env, 20)
    assert log == [(0, 'boggis'), (0, 'bunce'), (0, 'beans')]


def test_init_interrupt(env):
    """An interrupt should always be executed after an INIT event at the
    same time."""
    def child(env):
        try:
            yield env.timeout(10)
            pytest.fail('Should have been interrupted.')
        except simpy.Interrupt:
            assert env.now == 0

    def root(env):
        child_proc = env.start(child(env))
        child_proc.interrupt()

        yield env.timeout(1)

    env.start(root(env))
    simpy.simulate(env)


def test_interrupt_terminated_process(env):
    """A process that has no event scheduled cannot be interrupted."""
    def child(env):
        yield env.timeout(1)

    def parent(env):
        child_proc = env.start(child(env))

        yield env.timeout(2)
        ei = pytest.raises(RuntimeError, child_proc.interrupt)
        assert ei.value.args[0] == ('Process(child) has terminated '
                                    'and cannot be interrupted.')

        yield env.timeout(1)

    env.start(parent(env))
    simpy.simulate(env)


def test_multiple_interrupts(env):
    """Interrupts on dead processes are discarded. If there are multiple
    concurrent interrupts on a process and the latter dies after
    handling the first interrupt, the remaining ones are silently
    ignored.

    """
    def child(env):
        try:
            yield env.timeout(1)
        except simpy.Interrupt as i:
            env.exit(i.cause)

    def parent(env):
        c = env.start(child(env))
        yield env.timeout(0)
        c.interrupt(1)
        c.interrupt(2)
        result = yield c
        assert result == 1

    env.start(parent(env))
    simpy.simulate(env)


def test_interrupt_self(env):
    """A processs should not be able to interrupt itself."""
    def pem(env):
        pytest.raises(RuntimeError, env.active_process.interrupt)
        yield env.timeout(0)

    env.start(pem(env))
    simpy.simulate(env)


def test_immediate_interrupt(env, log):
    """Test should be interruptable immediatly after a suspend."""
    def child(env, log):
        try:
            yield env.suspend()
        except simpy.Interrupt:
            log.append(env.now)

    def resumer(env, other):
        other.interrupt()
        yield env.exit()

    c = env.start(child(env, log))
    env.start(resumer(env, c))
    simpy.simulate(env)

    # Confirm that child has been interrupted immediately at timestep 0.
    assert log == [0]


def test_interrupt_suspend(env):
    """A process should be interruptable during a suspend."""
    def child(env):
        try:
            yield env.suspend()
        except simpy.Interrupt:
            assert env.now == 5

    def parent(env):
        child_proc = env.start(child(env))
        yield env.timeout(5)
        child_proc.interrupt()

    env.start(parent(env))
    simpy.simulate(env)


def test_interrupt_event(env):
    """A process should be interruptable while waiting for an Event."""
    def child(env):
        try:
            yield env.event()
        except simpy.Interrupt:
            assert env.now == 5

    def parent(env):
        child_proc = env.start(child(env))
        yield env.timeout(5)
        child_proc.interrupt()

    env.start(parent(env))
    simpy.simulate(env)


def test_concurrent_behaviour(env):
    def proc_a(env):
        timeouts = [env.timeout(0) for i in range(2)]
        while timeouts:
            try:
                yield timeouts.pop(0)
                assert False, 'Expected an interrupt'
            except simpy.Interrupt:
                pass

    def proc_b(env, proc_a):
        for i in range(2):
            proc_a.interrupt()
        yield env.exit()

    proc_a = env.start(proc_a(env))
    env.start(proc_b(env, proc_a))

    simpy.simulate(env)
