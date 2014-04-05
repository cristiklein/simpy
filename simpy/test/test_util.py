"""
Tests for the utility functions from :mod:`simpy.util`.

"""
import re

import pytest

from simpy import Interrupt
from simpy.util import start_delayed, subscribe_at


def test_start_delayed(env):
    def pem(env):
        assert env.now == 5
        yield env.timeout(1)

    start_delayed(env, pem(env), delay=5)
    env.run()


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
        child_proc = env.process(child(env))
        subscribe_at(child_proc)

        try:
            yield env.event()
        except Interrupt as interrupt:
            assert interrupt.cause[0] is child_proc
            assert interrupt.cause[1] == 'ohai'
            assert env.now == 3

    env.process(parent(env))
    env.run()


def test_subscribe_terminated_proc(env):
    """subscribe() proc should send a singal immediatly if
    "other" has already terminated.

    """
    def child(env):
        yield env.timeout(1)

    def parent(env):
        child_proc = env.process(child(env))
        yield env.timeout(2)
        pytest.raises(RuntimeError, subscribe_at, child_proc)

    env.process(parent(env))
    env.run()


def test_subscribe_with_join(env):
    """Test that subscribe() works if a process waits for another one."""
    def child(env, i):
        yield env.timeout(i)

    def parent(env):
        child_proc1 = env.process(child(env, 1))
        child_proc2 = env.process(child(env, 2))
        try:
            subscribe_at(child_proc1)
            yield child_proc2
        except Interrupt as interrupt:
            assert env.now == 1
            assert interrupt.cause[0] is child_proc1
            assert child_proc2.is_alive

    env.process(parent(env))
    env.run()


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

    env.process(pem(env))
    env.run()


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

    env.process(pem(env))
    env.run()


def test_all_of(env):
    """Wait for all events to be triggered."""
    def parent(env):
        # Start 10 events.
        events = [env.timeout(i, value=i) for i in range(10)]
        results = yield env.all_of(events)

        assert results == {events[i]: i for i in range(10)}
        assert env.now == 9

    env.process(parent(env))
    env.run()


def test_wait_for_all_with_errors(env):
    """On default AllOf should fail immediately if one of its events
    fails."""
    def child_with_error(env, value):
        yield env.timeout(value)
        raise RuntimeError('crashing')

    def parent(env):
        events = [env.timeout(1, value=1),
                  env.process(child_with_error(env, 2)),
                  env.timeout(3, value=3)]

        try:
            condition = env.all_of(events)
            yield condition
            assert False, 'There should have been an exception'
        except RuntimeError as e:
            assert e.args[0] == 'crashing'

        # Although the condition has failed, interim values are available.
        assert condition._events[0].value == 1
        assert condition._events[1].value.args[0] == 'crashing'
        # The last child has not terminated yet.
        assert not events[2].processed

    env.process(parent(env))
    env.run()


def test_all_of_chaining(env):
    """If a wait_for_all condition A is chained to a wait_for_all condition B,
    B will be merged into A."""
    def parent(env):
        condition_A = env.all_of([env.timeout(i, value=i) for i in range(2)])
        condition_B = env.all_of([env.timeout(i, value=i) for i in range(2)])

        condition_A &= condition_B

        results = yield condition_A
        assert list(results.values()) == [0, 1, 0, 1]

    env.process(parent(env))
    env.run()


def test_all_of_chaining_intermediate_results(env):
    """If a wait_for_all condition A with intermediate results is merged into
    another wait_for_all condition B, the results are copied into condition
    A."""
    def parent(env):
        condition_A = env.all_of([env.timeout(i, value=i) for i in range(2)])
        condition_B = env.all_of([env.timeout(i, value=i) for i in range(2)])

        yield env.timeout(0)

        condition = condition_A & condition_B
        assert sorted(condition._get_values().values()) == [0, 0]

        results = yield condition
        assert sorted(results.values()) == [0, 0, 1, 1]

    env.process(parent(env))
    env.run()


def test_all_of_with_triggered_events(env):
    """Processed events can be added to a condition. Confirm this with
    all_of."""
    def parent(env):
        events = [env.timeout(0, value='spam'), env.timeout(1, value='eggs')]
        yield env.timeout(2)

        values = list((yield env.all_of(events)).values())
        assert values == ['spam', 'eggs']

    env.process(parent(env))
    env.run()


def test_any_of(env):
    """Wait for any event to be triggered."""
    def parent(env):
        # Start 10 events.
        events = [env.timeout(i, value=i) for i in range(10)]
        results = yield env.any_of(events)

        assert results == {events[0]: 0}
        assert env.now == 0

    env.process(parent(env))
    env.run()


def test_any_of_with_errors(env):
    """On default any_of should fail if the event has failed too."""
    def child_with_error(env, value):
        yield env.timeout(value)
        raise RuntimeError('crashing')

    def parent(env):
        events = [env.process(child_with_error(env, 1)),
                  env.timeout(2, value=2)]

        try:
            condition = env.any_of(events)
            yield condition
            assert False, 'There should have been an exception'
        except RuntimeError as e:
            assert e.args[0] == 'crashing'

        assert condition._events[0].value.args[0] == 'crashing'
        # The last event has not terminated yet.
        assert not events[1].processed

    env.process(parent(env))
    env.run()


def test_any_of_chaining(env):
    """If a any_of condition A is chained to a any_of condition B,
    B will be merged into A."""
    def parent(env):
        condition_A = env.any_of([env.timeout(2, value='a')])
        condition_B = env.any_of([env.timeout(1, value='b')])

        condition_A |= condition_B

        results = yield condition_A
        assert sorted(results.values()) == ['b']

    env.process(parent(env))
    env.run()


def test_any_of_with_triggered_events(env):
    """Processed events can be added to a condition. Confirm this with
    all_of."""
    def parent(env):
        events = [env.timeout(0, value='spam'), env.timeout(1, value='eggs')]
        yield env.timeout(2)

        values = list((yield env.any_of(events)).values())
        assert values == ['spam', 'eggs']

    env.process(parent(env))
    env.run()


def test_empty_any_of(env):
    """AnyOf will triggered immediately if there are no events."""
    def parent(env):
        results = yield env.any_of([])
        assert results == {}

    env.process(parent(env))
    env.run()


def test_empty_all_of(env):
    """AllOf will triggered immediately if there are no events."""
    def parent(env):
        results = yield env.all_of([])
        assert results == {}

    env.process(parent(env))
    env.run()


def test_all_of_expansion(env):
    """The result of AllOf is an OrderedDict, which allows to expand its values
    directly into variables."""
    def p(env):
        timeouts = [env.timeout(d, d) for d in [3, 2, 1]]
        a, b, c = (yield env.all_of(timeouts)).values()
        assert a == 3 and b == 2 and c == 1

    env.process(p(env))
    env.run()
