"""
Tests for the utility functions from :mod:`simpy.util`.

"""
import pytest

from simpy import Interrupt, simulate
from simpy.util import subscribe_at, wait_for_all, wait_for_any


def test_subscribe(env):
    """Check async. interrupt if a process terminates."""
    def child(env):
        yield env.hold(3)
        env.exit('ohai')

    def parent(env):
        child_proc = env.start(child(env))
        subscribe_at(child_proc)

        try:
            yield env.hold()
        except Interrupt as interrupt:
            assert interrupt.cause is child_proc
            assert child_proc.result == 'ohai'
            assert env.now == 3

    env.start(parent(env))
    simulate(env)


def test_subscribe_terminated_proc(env):
    """subscribe() proc should send a singal immediatly if
    "other" has already terminated.

    """
    def child(env):
        yield env.hold(1)

    def parent(env):
        child_proc = env.start(child(env))
        yield env.hold(2)
        pytest.raises(RuntimeError, subscribe_at, child_proc)

    env.start(parent(env))
    simulate(env)


def test_subscribe_with_join(env):
    """Test that subscribe() works if a process waits for another one."""
    def child(env, i):
        yield env.hold(i)

    def parent(env):
        child_proc1 = env.start(child(env, 1))
        child_proc2 = env.start(child(env, 2))
        try:
            subscribe_at(child_proc1)
            yield child_proc2
        except Interrupt as interrupt:
            assert env.now == 1
            assert interrupt.cause is child_proc1
            assert child_proc2.is_alive

    env.start(parent(env))
    simulate(env)


def test_join_any(env):
    def child(env, i):
        yield env.hold(i)
        env.exit(i)

    def parent(env):
        processes = [env.start(child(env, i)) for i in range(1, -1, -1)]

        for proc in processes:
            subscribe_at(proc)

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


def test_join_all_shortcut(env):
    """Test the shortcut function to wait until a number of procs finish."""
    def child(env, i):
        yield env.hold(i)
        env.exit(i)

    def parent(env):
        processes = [env.start(child(env, i)) for i in range(10)]

        results = yield wait_for_all(processes)

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
            finished, processes = yield wait_for_any(processes)
            assert finished.result == i
            assert len(processes) == (5 - i - 1)
            assert env.now == i

    env.start(parent(env))
    simulate(env)
