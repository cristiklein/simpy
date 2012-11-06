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


def test_concurrent_interrupts(env):
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

    log = []
    fantastic_mr_fox = env.start(fox(env, log))
    for name in ('boggis', 'bunce', 'beans'):
        env.start(farmer(env, name, fantastic_mr_fox))

    simpy.simulate(env, 20)
    assert log == [(0, 'boggis'), (0, 'bunce'), (0, 'beans')]
