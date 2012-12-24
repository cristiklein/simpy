from simpy import simulate
from simpy.core import wait_for_all, wait_for_any


# TODO Test behaviour of errors in nested expressions.

def test_wait_for_all(env):
    """Wait for all events to be triggered."""
    def parent(env):
        # Start 10 events.
        events = [env.timeout(i, value=i) for i in range(10)]
        results = yield wait_for_all(events)

        assert results == {events[i]: i for i in range(10)}
        assert env.now == 9

    env.start(parent(env))
    simulate(env)


def test_wait_for_all_with_errors(env):
    """On default wait_for_all should fail immediately if one of its events
    fails."""
    def child_with_error(env, value):
        yield env.timeout(value)
        raise RuntimeError('crashing')

    def parent(env):
        events = [env.timeout(1, value=1),
            env.start(child_with_error(env, 2)),
            env.timeout(3, value=3)]

        try:
            condition = wait_for_all(events)
            yield condition
            assert False, 'There should have been an exception'
        except RuntimeError as e:
            assert e.args[0] == 'crashing'

        # Although the condition has failed, intermediate results are
        # available.
        assert condition.results[events[0]] == 1
        assert condition.results[events[1]].args[0] == 'crashing'
        # The last child has not terminated yet.
        assert events[2] not in condition.results

    env.start(parent(env))
    simulate(env)


def test_wait_for_all_without_fail_on_error(env):
    """wait_for_all may also collect errors instead of failing immediately."""
    def child_with_error(env, value):
        yield env.timeout(value)
        raise RuntimeError('crashing')

    def parent(env):
        events = [env.start(child_with_error(env, 1)),
                env.timeout(2, value=2)]

        results = yield wait_for_all(events, fail_on_error=False)
        assert results[events[0]].args[0] == 'crashing'
        assert results[events[1]] == 2

    env.start(parent(env))
    simulate(env)


def test_wait_for_all_chaining(env):
    """If a wait_for_all condition A is chained to a wait_for_all condition B,
    B will be merged into A."""
    def parent(env):
        condition_A = wait_for_all([env.timeout(i, value=i) for i in range(2)])
        condition_B = wait_for_all([env.timeout(i, value=i) for i in range(2)])

        condition_A &= condition_B

        results = yield condition_A
        assert sorted(results.values()) == [0, 0, 1, 1]

    env.start(parent(env))
    simulate(env)


def test_wait_for_all_chaining_intermediate_results(env):
    """If a wait_for_all condition A with intermediate results is merged into
    another wait_for_all condition B, the results are copied into condition
    A."""
    def parent(env):
        condition_A = wait_for_all([env.timeout(i, value=i) for i in range(2)])
        condition_B = wait_for_all([env.timeout(i, value=i) for i in range(2)])

        yield env.timeout(0)

        condition = condition_A & condition_B
        assert sorted(condition.results.values()) == [0, 0]

        results = yield condition
        assert sorted(results.values()) == [0, 0, 1, 1]

    env.start(parent(env))
    simulate(env)


def test_wait_for_all_with_triggered_events(env):
    """Only pending events may be added to a wait_for_all condition."""
    def parent(env):
        event = env.timeout(1)
        yield env.timeout(2)

        try:
            wait_for_all([event])
            assert False, 'Expected an exception'
        except RuntimeError as e:
            assert e.args[0] == 'Event Timeout has already been triggered'

    env.start(parent(env))
    simulate(env)


def test_wait_for_any(env):
    """Wait for any event to be triggered."""
    def parent(env):
        # Start 10 events.
        events = [env.timeout(i, value=i) for i in range(10)]
        results = yield wait_for_any(events)

        assert results == {events[0]: 0}
        assert env.now == 0

    env.start(parent(env))
    simulate(env)


def test_wait_for_any_with_errors(env):
    """On default wait_for_any should fail if the event has failed too."""
    def child_with_error(env, value):
        yield env.timeout(value)
        raise RuntimeError('crashing')

    def parent(env):
        events = [env.start(child_with_error(env, 1)),
            env.timeout(2, value=2)]

        try:
            condition = wait_for_any(events)
            yield condition
            assert False, 'There should have been an exception'
        except RuntimeError as e:
            assert e.args[0] == 'crashing'

        assert condition.results[events[0]].args[0] == 'crashing'
        # The last event has not terminated yet.
        assert events[1] not in condition.results

    env.start(parent(env))
    simulate(env)


def test_wait_for_any_without_fail_on_error(env):
    """wait_for_any may also return the error of the failed event."""
    def child_with_error(env, value):
        yield env.timeout(value)
        raise RuntimeError('crashing')

    def parent(env):
        events = [env.start(child_with_error(env, 1)),
                env.timeout(2, value=2)]

        results = yield wait_for_any(events, fail_on_error=False)
        assert results[events[0]].args[0] == 'crashing'
        assert events[1] not in results

    env.start(parent(env))
    simulate(env)


def test_wait_for_any_chaining(env):
    """If a wait_for_any condition A is chained to a wait_for_any condition B,
    B will be merged into A."""
    def parent(env):
        condition_A = wait_for_any([env.timeout(i, value=i) for i in range(2)])
        condition_B = wait_for_any([env.timeout(i, value=i) for i in range(2)])

        condition_A |= condition_B

        results = yield condition_A
        assert sorted(results.values()) == [0]

    env.start(parent(env))
    simulate(env)


def test_wait_for_any_with_triggered_events(env):
    """Only pending events may be added to a wait_for_any condition."""
    def parent(env):
        event = env.timeout(1)
        yield env.timeout(2)

        try:
            wait_for_any([event])
            assert False, 'Expected an exception'
        except RuntimeError as e:
            assert e.args[0] == 'Event Timeout has already been triggered'

    env.start(parent(env))
    simulate(env)


def test_immutable_results(env):
    """Results of conditions should not change after they have been
    triggered."""
    def process(env):
        timeout = [env.timeout(delay, value=delay) for delay in range(3)]
        # The or condition in this expression will trigger immediately. The and
        # condition will trigger later on.
        condition = timeout[0] | (timeout[1] & timeout[2])

        yield condition
        assert condition.results == {
                timeout[0]: 0,
        }

        # Make sure that the results of condition were frozen. The results of
        # the nested and condition do not become visible afterwards.
        yield env.timeout(2)
        assert condition.results == {
                timeout[0]: 0,
        }

    env.start(process(env))
    simulate(env)


def test_operator_and(env):
    def process(env):
        timeout = [env.timeout(delay, value=delay) for delay in range(3)]
        results = yield timeout[0] & timeout[1] & timeout[2]

        assert results == {
                timeout[0]: 0,
                timeout[1]: 1,
                timeout[2]: 2,
        }

    env.start(process(env))
    simulate(env)


def test_operator_or(env):
    def process(env):
        timeout = [env.timeout(delay, value=delay) for delay in range(3)]
        results = yield timeout[0] | timeout[1] | timeout[2]

        assert results == {
                timeout[0]: 0,
        }

    env.start(process(env))
    simulate(env)


def test_operator_nested_and(env):
    def process(env):
        timeout = [env.timeout(delay, value=delay) for delay in range(3)]
        results = yield (timeout[0] & timeout[2]) | timeout[1]

        assert results == {
                timeout[0]: 0,
                timeout[1]: 1,
        }
        assert env.now == 1

    env.start(process(env))
    simulate(env)


def test_operator_nested_or(env):
    def process(env):
        timeout = [env.timeout(delay, value=delay) for delay in range(3)]
        results = yield (timeout[0] | timeout[1]) & timeout[2]

        assert results == {
                timeout[0]: 0,
                timeout[2]: 2,
        }
        assert env.now == 2

    env.start(process(env))
    simulate(env)


def test_shared_condition(env):
    timeout = [env.timeout(delay, value=delay) for delay in range(3)]
    c1 = timeout[0] | timeout[1]
    c2 = c1 & timeout[2]

    def p1(env, condition):
        results = yield condition
        assert results == {timeout[0]: 0}

    def p2(env, condition):
        results = yield condition
        assert results == {timeout[0]: 0, timeout[2]: 2}

    env.start(p1(env, c1))
    env.start(p2(env, c2))
    simulate(env)
