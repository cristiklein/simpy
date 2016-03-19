"""
Test asynchronous interrupts.

"""
import re

import pytest

import simpy


def test_interruption(env):
    """Processes can be interrupted while waiting for other events."""

    def interruptee(env):
        try:
            yield env.timeout(10)
            pytest.fail('Expected an interrupt')
        except simpy.Interrupt as interrupt:
            assert interrupt.cause == 'interrupt!'

    def interruptor(env):
        child_process = env.process(interruptee(env))
        yield env.timeout(5)
        child_process.interrupt('interrupt!')

    env.process(interruptor(env))
    env.run()


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

    fantastic_mr_fox = env.process(fox(env, log))
    for name in ('boggis', 'bunce', 'beans'):
        env.process(farmer(env, name, fantastic_mr_fox))

    env.run(20)
    assert log == [(0, 'boggis'), (0, 'bunce'), (0, 'beans')]


def test_concurrent_interrupts_and_events(env, log):
    """Interrupts interrupt a process while waiting for an event. Even if the
    event has happened concurrently with the interrupt."""

    def fox(env, coup, log):
        while True:
            try:
                yield coup
                log.append('coup completed at %d' % env.now)
                env.exit()
            except simpy.Interrupt:
                log.append('coup interrupted at %d' % env.now)

    def master_plan(env, fox, coup):
        yield env.timeout(1)
        # Succeed and interrupt concurrently.
        coup.succeed()
        fox.interrupt()

    coup = env.event()
    fantastic_mr_fox = env.process(fox(env, coup, log))
    env.process(master_plan(env, fantastic_mr_fox, coup))

    env.run(5)
    assert log == ['coup interrupted at 1', 'coup completed at 1']


def test_init_interrupt(env):
    """An interrupt should always be executed after the Initialize event at the
    same time."""
    def child(env):
        try:
            yield env.timeout(10)
            pytest.fail('Should have been interrupted.')
        except simpy.Interrupt:
            assert env.now == 0

    def root(env):
        child_proc = env.process(child(env))
        child_proc.interrupt()

        yield env.timeout(1)

    env.process(root(env))
    env.run()


def test_interrupt_terminated_process(env):
    """Dead processes cannot be interrupted."""

    def child(env):
        yield env.timeout(1)

    def parent(env):
        child_proc = env.process(child(env))

        # Wait long enough so that child_proc terminates.
        yield env.timeout(2)
        ei = pytest.raises(RuntimeError, child_proc.interrupt)
        assert re.match(r'<Process\(child\) object at 0x.*> has terminated '
                        r'and cannot be interrupted.', ei.value.args[0])

        yield env.timeout(1)

    env.process(parent(env))
    env.run()


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
        c = env.process(child(env))
        yield env.timeout(0)
        c.interrupt(1)
        c.interrupt(2)
        result = yield c
        assert result == 1

    env.process(parent(env))
    env.run()


def test_interrupt_self(env):
    """A process should not be able to interrupt itself."""
    def pem(env):
        pytest.raises(RuntimeError, env.active_process.interrupt)
        yield env.timeout(0)

    env.process(pem(env))
    env.run()


def test_immediate_interrupt(env, log):
    """Processes are immediately interruptable."""
    def child(env, log):
        try:
            yield env.event()
        except simpy.Interrupt:
            log.append(env.now)

    def parent(env, log):
        child_proc = env.process(child(env, log))
        child_proc.interrupt()
        yield env.exit()

    env.process(parent(env, log))
    env.run()

    # Confirm that child has been interrupted immediately at timestep 0.
    assert log == [0]


def test_interrupt_event(env):
    """A process should be interruptable while waiting for an Event."""
    def child(env):
        try:
            yield env.event()
        except simpy.Interrupt:
            assert env.now == 5

    def parent(env):
        child_proc = env.process(child(env))
        yield env.timeout(5)
        child_proc.interrupt()

    env.process(parent(env))
    env.run()


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

    proc_a = env.process(proc_a(env))
    env.process(proc_b(env, proc_a))

    env.run()
