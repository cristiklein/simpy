# encoding: utf-8
"""
API tests for the interaction of multiple processes.

"""
# Pytest gets the parameters "sim" and "log" from the *conftest.py* file
import pytest

import simpy


pytest_plugins = ['simpy.test.support']


def test_interruption(ctx):
    """With asynchronous interrupts, the victim expects an interrupt
    while waiting for an event, but will process this even if no
    interrupt occured.

    """
    def interruptee(ctx):
        try:
            yield ctx.wait(10)
            pytest.fail('Expected an interrupt')
        except simpy.Interrupt as interrupt:
            assert interrupt.cause == 'interrupt!'

    child_process = ctx.start(interruptee(ctx))
    yield ctx.wait(5)
    child_process.interrupt('interrupt!')


def test_concurrent_interrupts(ctx):
    """Concurrent interrupts are scheduled in the order in which they occured.
    """
    def fox(ctx, log):
        while True:
            try:
                yield ctx.wait(10)
            except simpy.Interrupt as interrupt:
                log.append(interrupt.cause)

    def farmer(ctx, name, fox):
        fox.interrupt(name)
        yield ctx.wait(1)

    log = []
    fantastic_mr_fox = ctx.start(fox(ctx, log))
    farmers = [ctx.start(farmer(ctx, name, fantastic_mr_fox))
            for name in ('boggis', 'bunce', 'beans')]

    for farmer in farmers:
        yield farmer

    assert log == ['boggis', 'bunce', 'beans']


def test_suspend_interrupt(ctx):
    """If a process passivates itself, it will no longer get active by
    itself but needs to be interrupted by another process.

    """
    def sleeper(ctx):
        yield ctx.suspend()
        assert ctx.now == 10

    sleeper = ctx.start(sleeper(ctx))
    yield ctx.wait(10)
    sleeper.interrupt()


def test_wait_for_proc(ctx):
    """A process can wait until another process finishes."""
    def finisher(ctx):
        yield ctx.wait(5)

    proc = ctx.start(finisher(ctx))
    yield proc  # Waits until "proc" finishes

    assert ctx.now == 5


def test_get_process_state(ctx):
    """A process may be *active* (has event scheduled), *passive* (has
    no event scheduled) or *terminated* (PEM generator stopped).

    """
    def child(ctx):
        yield ctx.wait(3)

    child = ctx.start(child(ctx))
    yield ctx.wait(1)
    assert child.is_alive

    yield ctx.wait(3)
    assert not child.is_alive


def test_return_value(ctx):
    """Processes can set a return value via an ``exit()`` function,
    comparable to ``sys.exit()``.

    """
    def child(ctx):
        yield ctx.wait(1)
        ctx.exit(ctx.now)

    result1 = yield ctx.start(child(ctx))
    result2 = yield ctx.start(child(ctx))

    assert [result1, result2] == [1, 2]
