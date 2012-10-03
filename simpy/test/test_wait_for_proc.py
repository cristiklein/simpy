"""
Tests for waiting for a process to finish.

"""
import pytest

from simpy import Interrupt, simulate
from simpy.util import wait_for_all, wait_for_any


def test_wait_for_proc(env):
    """A process can wait until another process finishes."""
    def finisher(env):
        yield env.hold(5)

    def waiter(env, finisher):
        proc = env.start(finisher(env))
        yield proc  # Waits until "proc" finishes

        assert env.now == 5

    env.start(waiter(env, finisher))
    simulate(env)


def test_return_value(env):
    """Processes can set a return value via an ``exit()`` function,
    comparable to ``sys.exit()``.

    """
    def child(env):
        yield env.hold(1)
        env.exit(env.now)

    def parent(env):
        result1 = yield env.start(child(env))
        result2 = yield env.start(child(env))

        assert [result1, result2] == [1, 2]

    env.start(parent(env))
    simulate(env)


def test_illegal_wait(env):
    """Raise an error if a process forget to yield an event before it
    starts waiting for a process.

    """
    def child(env):
        yield env.hold(1)

    def parent(env):
        env.hold(1)
        yield env.start(child(env))

    env.start(parent(env))
    pytest.raises(RuntimeError, simulate, env)


def test_join_after_terminate(env):
    """Waiting for an already terminated process should return
    immediately.

    """
    def child(env):
        yield env.hold(1)

    def parent(env):
        child_proc = env.start(child(env))
        yield env.hold(2)
        yield child_proc

        assert env.now == 2

    env.start(parent(env))
    simulate(env)


def test_join_all(env):
    """Test waiting for multiple processes."""
    def child(env, i):
        yield env.hold(i)
        env.exit(i)

    def parent(env):
        processes = [env.start(child(env, i)) for i in range(9, -1, -1)]

        # Wait for all processes to terminate.
        results = []
        for proc in processes:
            results.append((yield proc))

        assert results == list(reversed(range(10)))
        assert env.now == 9

    env.start(parent(env))
    simulate(env)


def test_join_any(env):
    def child(env, i):
        yield env.hold(i)
        env.exit(i)

    def parent(env):
        processes = [env.start(child(env, i)) for i in range(9, -1, -1)]

        for proc in processes:
            env.interrupt_on(proc)

        try:
            yield env.hold()
            pytest.fail('There should have been an interrupt')
        except Interrupt as interrupt:
            first_dead = interrupt.cause
            assert first_dead is processes[-1]
            assert first_dead.result == 0
            assert env.now == 0

    env.start(parent(env))
    simulate(env)


def test_child_exception(env):
    """A child catches an exception and sends it to its parent."""
    def child(env):
        try:
            yield env.hold(1)
            raise RuntimeError('Onoes!')
        except RuntimeError as err:
            env.exit(err)

    def parent(env):
        result = yield env.start(child(env))
        assert isinstance(result, Exception)

    env.start(parent(env))
    simulate(env)


def test_illegal_hold_followed_by_join(env):
    """Check that an exception is raised if a "yield proc" follows on an
    illegal hold()."""
    def child(env):
        yield env.hold(1)

    def parent(env):
        env.hold(1)
        yield env.start(child(env))

    env.start(parent(env))
    ei = pytest.raises(RuntimeError, simulate, env)
    # Assert that the exceptino was correctly thwon into the PEM
    assert "yield env.start(child(env))" in str(ei.traceback[-1])


def test_interrupt_on(env):
    """Check async. interrupt if a process terminates."""
    def child(env):
        yield env.hold(3)
        env.exit('ohai')

    def parent(env):
        child_proc = env.start(child(env))
        env.interrupt_on(child_proc)

        try:
            yield env.hold()
        except Interrupt as interrupt:
            assert interrupt.cause is child_proc
            assert child_proc.result == 'ohai'
            assert env.now == 3

    env.start(parent(env))
    simulate(env)


def test_interrupt_on_terminated_proc(env):
    """interrupt_on(other) proc should send a singal immediatly if
    "other" has already terminated.

    """
    def child(env):
        yield env.hold(1)

    def parent(env):
        child_proc = env.start(child(env))
        yield env.hold(2)
        try:
            env.interrupt_on(child_proc)
            assert env.now == 2
            yield env.hold()
            pytest.fail('Did not get an Interrupt.')
        except Interrupt:
            assert env.now == 2

    env.start(parent(env))
    simulate(env)


def test_interrupted_join(env):
    """Tests that interrupts are raised while the victim is waiting for
    another process.

    """
    def interruptor(env, process):
        yield env.hold(1)
        process.interrupt()

    def child(env):
        yield env.hold(2)

    def parent(env):
        child_proc = env.start(child(env))
        try:
            yield child_proc
            pytest.fail('Did not receive an interrupt.')
        except Interrupt:
            assert env.now == 1
            assert child_proc.is_alive

    parent_proc = env.start(parent(env))
    env.start(interruptor(env, parent_proc))
    simulate(env)


def test_interrupt_on_with_join(env):
    """Test that interrupt_on() works if a process waits for another one."""
    def child(env, i):
        yield env.hold(i)

    def parent(env):
        child_proc1 = env.start(child(env, 1))
        child_proc2 = env.start(child(env, 2))
        try:
            env.interrupt_on(child_proc1)
            yield child_proc2
        except Interrupt as interrupt:
            assert env.now == 1
            assert interrupt.cause is child_proc1
            assert child_proc2.is_alive

    env.start(parent(env))
    simulate(env)


def test_join_all_shortcut(env):
    """Test the shortcut function to wait until a number of procs finish."""
    def child(env, i):
        yield env.hold(i)
        env.exit(i)

    def parent(env):
        processes = [env.start(child(env, i)) for i in range(10)]

        results = yield wait_for_all(env, processes)

        assert results == list(range(10))
        assert env.now == 9

    env.start(parent(env))
    simulate(env)


def test_join_any_shortcut(env):
    """Test the shortcut function to wait for any of a number of procs."""
    def child(env, i):
        yield env.hold(i)
        env.exit(i)

    def parent(env):
        processes = [env.start(child(env, i)) for i in [4, 1, 2, 0, 3]]

        for i in range(5):
            finished, processes = yield wait_for_any(env, processes)
            assert finished.result == i
            assert len(processes) == (5 - i - 1)
            assert env.now == i

    env.start(parent(env))
    simulate(env)
