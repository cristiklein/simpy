"""
Tests for the utility functions from :mod:`simpy.util`.

"""
import pytest

from simpy import Interrupt, simulate
from simpy.util import start_delayed, subscribe_at


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
