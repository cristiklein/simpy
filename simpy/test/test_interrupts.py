"""
Test asynchronous interrupts.

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
    """Concurrent interrupts are scheduled in the order in which they
    occured.

    """
    def fox(context, log):
        while True:
            try:
                yield context.hold(10)
            except simpy.Interrupt as interrupt:
                log.append((context.now, interrupt.cause))

    def farmer(context, name, fox):
        context.interrupt(fox, name)
        yield context.hold(1)

    fantastic_mr_fox = sim.start(fox, log)
    for name in ('boggis', 'bunce', 'beans'):
        sim.start(farmer, name, fantastic_mr_fox)

    sim.simulate(20)
    assert log == [(0, 'boggis'), (0, 'bunce'), (0, 'beans')]


def test_illegal_interrupt(sim):
    """A process that was just started cannot be interrupted."""
    def child(context):
        yield context.hold(10)

    def root(context):
        child_proc = context.start(child)
        ei = pytest.raises(RuntimeError, context.interrupt, child_proc)
        assert ei.value.args[0] == ('Process(1, child) was just initialized '
                                    'and cannot yet be interrupted.')

        yield context.hold(1)

    sim.start(root)
    sim.simulate()


def test_interrupt_terminated_process(sim):
    """A process that has no event scheduled cannot be interrupted."""
    def child(context):
        yield context.hold(1)

    def parent(context):
        child_proc = context.start(child)

        yield context.hold(2)
        ei = pytest.raises(RuntimeError, context.interrupt, child_proc)
        assert ei.value.args[0] == ('Process(1, child) has no event scheduled '
                                    'and cannot be interrupted.')

        yield context.hold(1)

    sim.start(parent)
    sim.simulate()


def test_interrupt_suspended_proces(sim):
    """A suspended process cannot be interrupted."""
    def child(context):
        yield context.suspend()

    def parent(context):
        child_proc = context.start(child)

        yield context.hold(1)
        ei = pytest.raises(RuntimeError, context.interrupt, child_proc)
        assert ei.value.args[0] == ('Process(1, child) is suspended and '
                                    'cannot be interrupted.')

    sim.start(parent)
    sim.simulate()
