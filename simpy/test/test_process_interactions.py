# encoding: utf-8
"""
API tests for the interaction of multiple processes.

"""
# Pytest gets the parameters "sim" and "log" from the *conftest.py* file
import pytest

import simpy


def test_interruption(sim):
    """With asynchronous interrupts, the victim expects an interrupt
    while waiting for an event, but will process this even if no
    interrupt occured.

    """
    def interruptee(context):
        try:
            yield context.hold(10)
            pytest.fail('Expected an interrupt')
        except simpy.Interrupt as interrupt:
            assert interrupt.cause == 'interrupt!'

    def interruptor(context):
        child_process = context.start(interruptee)
        yield context.hold(5)
        context.interrupt(child_process, 'interrupt!')

    sim.start(interruptor)
    sim.simulate(until=30)


def test_concurrent_interrupts(sim, log):
    """Concurrent interrupts are scheduled in the order in which they occured.
    """
    def fox(context, log):
        while True:
            try:
                yield context.hold(10)
            except simpy.Interrupt as interrupt:
                log.append(interrupt.cause)

    def farmer(context, name, fox):
        context.interrupt(fox, name)
        yield context.hold(1)

    fantastic_mr_fox = sim.start(fox, log)
    for name in ('boggis', 'bunce', 'beans'):
        sim.start(farmer, name, fantastic_mr_fox)

    sim.simulate(20)
    assert log == ['boggis', 'bunce', 'beans']


@pytest.mark.xfail
def test_suspend_resume(sim):
    """If a process passivates itself, it will no longer get active by
    itself but needs to be reactivated by another process (in contrast
    to interrupts, where the interrupt may or may not occur).

    """
    def sleeper(context):
        yield context.suspend()
        assert context.now == 10

    def alarm(context, sleeper):
        yield context.hold(10)
        context.resume(sleeper)

    sleeper = sim.start(sleeper)
    sim.start(alarm, sleeper)
    sim.simulate()


def test_wait_for_proc(sim):
    """A process can wait until another process finishes."""
    def finisher(context):
        yield context.hold(5)

    def waiter(context, finisher):
        proc = context.start(finisher)
        yield proc  # Waits until "proc" finishes

        assert context.now == 5

    sim.start(waiter, finisher)
    sim.simulate()


@pytest.mark.xfail
def test_get_process_state(sim):
    """A process may be *active* (has event scheduled), *passive* (has
    no event scheduled) or *terminated* (PEM generator stopped).

    """
    def pem_a(context):
        yield context.hold(3)

    def pem_b(context, pem_a):
        yield context.hold(1)
        assert pem_a.is_alive

        yield context.hold(3)
        assert not pem_a.is_alive

    proc_a = sim.start(pem_a)
    sim.start(pem_b, proc_a)
    sim.simulate()


def test_return_value(sim):
    """Processes can set a return value via an ``exit()`` function,
    comparable to ``sys.exit()``.

    """
    def child(context):
        yield context.hold(1)
        context.exit(context.now)

    def parent(context):
        result1 = yield context.start(child)
        result2 = yield context.start(child)

        assert [result1, result2] == [1, 2]

    sim.start(parent)
    sim.simulate()
