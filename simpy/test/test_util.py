"""
Tests for the utility functions from :mod:`simpy.util`.

"""
import random

import pytest

from simpy import Interrupt, simulate
from simpy.core import WaitForAll
from simpy.util import start_delayed, subscribe_at, wait_for_all, wait_for_any


def test_start_delayed(env):
    def pem(env):
        assert env.now == 5
        yield env.timeout(1)

    start_delayed(env, pem(env), delay=5)
    simulate(env)


def test_start_delayed_error(env):
    """Check if delayed() raises an error if you pass a negative dt."""
    def pem(env):
        yield env.timeout(1)

    pytest.raises(ValueError, start_delayed, env, pem(env), delay=-1)


def test_subscribe(env):
    """Check async. interrupt if a process terminates."""
    def child(env):
        yield env.timeout(3)
        env.exit('ohai')

    def parent(env):
        child_proc = env.start(child(env))
        subscribe_at(child_proc)

        try:
            yield env.suspend()
        except Interrupt as interrupt:
            assert interrupt.cause[0] is child_proc
            assert interrupt.cause[1] == 'ohai'
            assert env.now == 3

    env.start(parent(env))
    simulate(env)


def test_subscribe_terminated_proc(env):
    """subscribe() proc should send a singal immediatly if
    "other" has already terminated.

    """
    def child(env):
        yield env.timeout(1)

    def parent(env):
        child_proc = env.start(child(env))
        yield env.timeout(2)
        pytest.raises(RuntimeError, subscribe_at, child_proc)

    env.start(parent(env))
    simulate(env)


def test_subscribe_with_join(env):
    """Test that subscribe() works if a process waits for another one."""
    def child(env, i):
        yield env.timeout(i)

    def parent(env):
        child_proc1 = env.start(child(env, 1))
        child_proc2 = env.start(child(env, 2))
        try:
            subscribe_at(child_proc1)
            yield child_proc2
        except Interrupt as interrupt:
            assert env.now == 1
            assert interrupt.cause[0] is child_proc1
            assert child_proc2.is_alive

    env.start(parent(env))
    simulate(env)


def test_subscribe_at_timeout(env):
    """You should be able to subscribe at arbitrary events."""
    def pem(env):
        to = env.timeout(2)
        subscribe_at(to)
        try:
            yield env.timeout(10)
        except Interrupt as interrupt:
            assert interrupt.cause == (to, None)
            assert env.now == 2

    env.start(pem(env))
    simulate(env)


def test_subscribe_at_timeout_with_value(env):
    """An event's value should be accessible via the interrupt cause."""
    def pem(env):
        val = 'ohai'
        to = env.timeout(2, value=val)
        subscribe_at(to)
        try:
            yield env.timeout(10)
        except Interrupt as interrupt:
            assert interrupt.cause == (to, val)
            assert env.now == 2

    env.start(pem(env))
    simulate(env)


def test_join_any(env):
    def child(env, i):
        yield env.timeout(i)
        env.exit(i)

    def parent(env):
        processes = [env.start(child(env, i)) for i in range(1, -1, -1)]

        for proc in processes:
            subscribe_at(proc)

        try:
            yield env.suspend()
            pytest.fail('There should have been an interrupt')
        except Interrupt as interrupt:
            first_dead, result = interrupt.cause
            assert first_dead is processes[-1]
            assert result == 0
            assert env.now == 0

    env.start(parent(env))
    simulate(env)


def test_wait_for_all(env):
    """Test the shortcut function to wait until a number of procs finish."""
    def child(env, value, delay):
        yield env.timeout(delay)
        env.exit(value)

    def parent(env):
        # Start 10 children. The children wait a decreasing amount of time.
        children = [env.start(child(env, i, 10 - i)) for i in range(10)]

        # Wait for all children and ensure that the order of the results does
        # depend on the order they were passed into wait_for_all and not on the
        # order in which they terminated.
        results = yield WaitForAll(children)

        assert results == {children[i]: i for i in range(10)}
        assert env.now == 10

    env.start(parent(env))
    simulate(env)


def test_wait_for_all_with_errors(env):
    """Test the shortcut function to wait until a number of procs finish."""
    def child(env, value, delay):
        yield env.timeout(delay)
        env.exit(value)

    def child_with_error(env, delay):
        yield env.timeout(delay)
        raise RuntimeError('crashing')

    def parent(env):
        children = [env.start(child(env, 1, 1)),
            env.start(child_with_error(env, 2)),
            env.start(child(env, 2, 2))]

        # By default wait_for_all will terminate immediately if one of the
        # events has failed.
        try:
            results = yield WaitForAll(children)
            assert False, 'There should have been an exception'
        except RuntimeError as e:
            assert e.args[0] == 'crashing'

    env.start(parent(env))
    simulate(env)


def test_wait_for_all_with_timeout(env):
    """wait_for_all may optionally cancel after a given timeout. After the
    timeout all intermediate results are returned."""
    def child(env, value, delay):
        yield env.timeout(delay)
        env.exit(value)

    def parent(env):
        # Start four children which wait up to three time units.
        children = [env.start(child(env, i, i)) for i in range(4)]

        # Wait until all children have terminated or two time units have
        # passed.
        # FIXME Should we raise an exception on timeout instead?
        # FIXME Should we declare a special value for untriggered events? None
        # is also a valid result of an event.
        results = yield wait_for_all(children, timeout=2)
        assert results == [0, 1, None, None]

    env.start(parent(env))
    simulate(env)


def test_wait_for_any(env):
    """Test the shortcut function to wait for any of a number of procs."""
    def child(env, i):
        yield env.timeout(i)
        env.exit(i)

    def parent(env):
        processes = [env.start(child(env, i)) for i in [4, 1, 2, 0, 3]]

        for i in range(5):
            finished_proc, result = yield wait_for_any(processes)
            processes.remove(finished_proc)
            assert result == i
            assert env.now == i

    env.start(parent(env))
    simulate(env)


def test_wait_for_any_timeout(env):
    def child(env, i):
        yield env.timeout(i)
        env.exit(i)

    def parent(env):
        events = [env.timeout(2)]

        # FIXME A timeout exception is probably really better...
        result = yield wait_for_any(events, timeout=1)
        assert result == None
        assert env.now == 1

    env.start(parent(env))
    simulate(env)


def test_start_delayed_with_wait_for_all(env):
    """Test waiting for all instances of delayed processes."""
    def child(env):
        yield env.timeout(1)

    def parent(env):
        procs = WaitForAll(
                    start_delayed(env, child(env), i) for i in range(3))
        for proc in procs:
            assert proc.name == 'child'


def test_wait_for_any_with_mixed_events(env):
    """wait_for_any should work with processes and normal events."""
    def child(env):
        yield env.timeout(2)

    def parent(env):
        child_proc = env.start(child(env))
        timeout = env.timeout(1)
        result = yield wait_for_any([child_proc, timeout])
        assert result == (timeout, None)

    env.start(parent(env))
    simulate(env)


def test_wait_for_all_with_mixed_events(env):
    """wait_for_any should work with processes and normal events."""
    def child(env):
        yield env.timeout(2)
        env.exit('eggs')

    def parent(env):
        child_proc = env.start(child(env))
        timeout = env.timeout(1, 'spam')
        result = yield wait_for_all([child_proc, timeout])
        assert result == ['eggs', 'spam']

    env.start(parent(env))
    simulate(env)


def test_operator_and(env):
    def process(env):
        timeout = [env.timeout(delay) for delay in range(3)]
        results = yield timeout[0] & timeout[1] & timeout[2]

        assert results == {
                timeout[0]: None,
                timeout[1]: None,
                timeout[2]: None,
        }

    env.start(process(env))
    simulate(env)


def test_operator_and_merge(env):
    def process(env):
        timeout = [env.timeout(delay) for delay in range(4)]
        condition_1 = timeout[0] & timeout[1]
        condition_2 = timeout[2] & timeout[3]
        condition = condition_1 & condition_2

        # Wait for all conditions are merged.
        assert condition is condition_1
        results = yield condition

        assert results == {
                timeout[0]: None,
                timeout[1]: None,
                timeout[2]: None,
                timeout[3]: None,
        }

    env.start(process(env))
    simulate(env)


def test_operator_and_extend(env):
    def process(env):
        timeout = [env.timeout(delay) for delay in range(4)]
        condition = timeout[0] & timeout[1] & timeout[2]
        yield env.timeout(1)
        assert condition.results == {
                timeout[0]: None,
                timeout[1]: None,
        }

        condition &= timeout[3]
        results = yield condition

        assert results == {
                timeout[0]: None,
                timeout[1]: None,
                timeout[2]: None,
                timeout[3]: None,
        }

    env.start(process(env))
    simulate(env)


def test_operator_or(env):
    def process(env):
        timeout = [env.timeout(delay) for delay in range(3)]
        results = yield timeout[0] | timeout[1] | timeout[2]

        assert results == {
                timeout[0]: None,
        }

    env.start(process(env))
    simulate(env)


def test_operator_or_extend(env):
    def process(env):
        timeout = [env.timeout(delay) for delay in range(4)]
        condition = timeout[0] | timeout[1] | timeout[2]
        yield env.timeout(1)
        assert condition.results == {
                timeout[0]: None,
        }

        try:
            condition |= timeout[3]
            assert False, 'Expected an exception'
        except RuntimeError as e:
            assert e.args[0] == ('Event WaitForAny(Timeout, Timeout, Timeout) '
                    'has already been triggered')

    env.start(process(env))
    simulate(env)


def test_operator_nested(env):
    def process(env):
        timeout = [env.timeout(delay) for delay in range(3)]
        results = yield (timeout[0] & timeout[2]) | timeout[1]

        assert results == {
                timeout[0]: None,
                timeout[1]: None,
        }

    env.start(process(env))
    simulate(env)
