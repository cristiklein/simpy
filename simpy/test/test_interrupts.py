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
            yield env.hold(10)
            pytest.fail('Expected an interrupt')
        except simpy.Interrupt as interrupt:
            assert interrupt.cause == 'interrupt!'

    def interruptor(env):
        child_process = env.start(interruptee(env))
        yield env.hold(5)
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
                yield env.hold(10)
            except simpy.Interrupt as interrupt:
                log.append((env.now, interrupt.cause))

    def farmer(env, name, fox):
        fox.interrupt(name)
        yield env.hold(1)

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
            yield env.hold(10)
            pytest.fail('Should have been interrrupted.')
        except simpy.Interrupt:
            assert env.now == 0

    def root(env):
        child_proc = env.start(child(env))
        child_proc.interrupt()

        yield env.hold(1)

    env.start(root(env))
    simpy.simulate(env)


def test_interrupt_terminated_process(env):
    """A process that has no event scheduled cannot be interrupted."""
    def child(env):
        yield env.hold(1)

    def parent(env):
        child_proc = env.start(child(env))

        yield env.hold(2)
        ei = pytest.raises(RuntimeError, child_proc.interrupt)
        assert ei.value.args[0] == ('Process(child) has terminated '
                                    'and cannot be interrupted.')

        yield env.hold(1)

    env.start(parent(env))
    simpy.simulate(env)


def test_multiple_interrupts(env):
    """SimPy should detect if a process gets interrupted twice, but
    terminates after the first one.

    """
    def child(env):
        try:
            yield env.hold(1)
        except simpy.Interrupt:
            env.exit('spam')

    def parent(env):
        c = env.start(child(env))
        yield env.hold(0)
        c.interrupt(1)
        c.interrupt(2)
        result = yield c
        assert result == 'spam'

    env.start(parent(env))
    pytest.raises(RuntimeError, simpy.simulate, env)


def test_interrupt_self(env):
    """A processs should not be able to interrupt itself."""
    def pem(env):
        pytest.raises(RuntimeError, env.active_process.interrupt)
        yield env.hold(0)

    env.start(pem(env))
    simpy.simulate(env)
