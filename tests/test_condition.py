import pytest


def test_operator_and(env):
    def process(env):
        timeout = [env.timeout(delay, value=delay) for delay in range(3)]
        results = yield timeout[0] & timeout[1] & timeout[2]

        assert results == {
            timeout[0]: 0,
            timeout[1]: 1,
            timeout[2]: 2,
        }

    env.process(process(env))
    env.run()


def test_operator_and_blocked(env):
    def process(env):
        timeout = env.timeout(1)
        event = env.event()
        yield env.timeout(1)

        condition = timeout & event
        assert not condition.triggered

    env.process(process(env))
    env.run()


def test_operator_or(env):
    def process(env):
        timeout = [env.timeout(delay, value=delay) for delay in range(3)]
        results = yield timeout[0] | timeout[1] | timeout[2]

        assert results == {
            timeout[0]: 0,
        }

    env.process(process(env))
    env.run()


def test_operator_nested_and(env):
    def process(env):
        timeout = [env.timeout(delay, value=delay) for delay in range(3)]
        results = yield (timeout[0] & timeout[2]) | timeout[1]

        assert results == {
            timeout[0]: 0,
            timeout[1]: 1,
        }
        assert env.now == 1

    env.process(process(env))
    env.run()


def test_operator_nested_or(env):
    def process(env):
        timeout = [env.timeout(delay, value=delay) for delay in range(3)]
        results = yield (timeout[0] | timeout[1]) & timeout[2]

        assert results == {
            timeout[0]: 0,
            timeout[1]: 1,
            timeout[2]: 2,
        }
        assert env.now == 2

    env.process(process(env))
    env.run()


def test_nested_cond_with_error(env):
    def explode(env):
        yield env.timeout(1)
        raise ValueError('Onoes!')

    def process(env):
        try:
            yield env.process(explode(env)) & env.timeout(1)
            pytest.fail('The condition should have raised a ValueError')
        except ValueError as err:
            assert err.args == ('Onoes!',)

    env.process(process(env))
    env.run()


def test_cond_with_error(env):
    def explode(env, delay):
        yield env.timeout(delay)
        raise ValueError('Onoes, failed after %d!' % delay)

    def process(env):
        try:
            yield env.process(explode(env, 0)) | env.timeout(1)
            pytest.fail('The condition should have raised a ValueError')
        except ValueError as err:
            assert err.args == ('Onoes, failed after 0!',)

    env.process(process(env))
    env.run()


def test_cond_with_nested_error(env):
    def explode(env, delay):
        yield env.timeout(delay)
        raise ValueError('Onoes, failed after %d!' % delay)

    def process(env):
        try:
            yield (env.process(explode(env, 0)) & env.timeout(1) |
                   env.timeout(1))
            pytest.fail('The condition should have raised a ValueError')
        except ValueError as err:
            assert err.args == ('Onoes, failed after 0!',)

    env.process(process(env))
    env.run()


def test_cond_with_uncaught_error(env):
    """Errors that happen after the condition has been triggered will not be
    handled by the condition and cause the simulation to crash."""
    def explode(env, delay):
        yield env.timeout(delay)
        raise ValueError('Onoes, failed after %d!' % delay)

    def process(env):
        yield env.timeout(1) | env.process(explode(env, 2))

    env.process(process(env))
    try:
        env.run()
        assert False, 'There should have been an exception.'
    except ValueError:
        pass
    assert env.now == 2


def test_iand_with_and_cond(env):
    def process(env):
        cond = env.timeout(1, value=1) & env.timeout(2, value=2)
        orig = cond

        cond &= env.timeout(0, value=0)
        assert cond is not orig

        results = yield cond
        assert list(results.values()) == [1, 2, 0]

    env.process(process(env))
    env.run()


def test_iand_with_or_cond(env):
    def process(env):
        cond = env.timeout(1, value=1) | env.timeout(2, value=2)
        orig = cond

        cond &= env.timeout(0, value=0)
        assert cond is not orig

        results = yield cond
        assert list(results.values()) == [1, 0]

    env.process(process(env))
    env.run()


def test_ior_with_or_cond(env):
    def process(env):
        cond = env.timeout(1, value=1) | env.timeout(2, value=2)
        orig = cond

        cond |= env.timeout(0, value=0)
        assert cond is not orig

        results = yield cond
        assert list(results.values()) == [0]

    env.process(process(env))
    env.run()


def test_ior_with_and_cond(env):
    def process(env):
        cond = env.timeout(1, value=1) & env.timeout(2, value=2)
        orig = cond

        cond |= env.timeout(0, value=0)
        assert cond is not orig

        results = yield cond
        assert list(results.values()) == [0]

    env.process(process(env))
    env.run()


def test_immutable_results(env):
    """Results of conditions should not change after they have been
    triggered."""
    def process(env):
        timeout = [env.timeout(delay, value=delay) for delay in range(3)]
        # The or condition in this expression will trigger immediately. The and
        # condition will trigger later on.
        condition = timeout[0] | (timeout[1] & timeout[2])

        results = yield condition
        assert results == {timeout[0]: 0}

        # Make sure that the results of condition were frozen. The results of
        # the nested and condition do not become visible afterwards.
        yield env.timeout(2)
        assert results == {timeout[0]: 0}

    env.process(process(env))
    env.run()


def test_shared_and_condition(env):
    timeout = [env.timeout(delay, value=delay) for delay in range(3)]
    c1 = timeout[0] & timeout[1]
    c2 = c1 & timeout[2]

    def p1(env, condition):
        results = yield condition
        assert results == {timeout[0]: 0, timeout[1]: 1}

    def p2(env, condition):
        results = yield condition
        assert results == {timeout[0]: 0, timeout[1]: 1, timeout[2]: 2}

    env.process(p1(env, c1))
    env.process(p2(env, c2))
    env.run()


def test_shared_or_condition(env):
    timeout = [env.timeout(delay, value=delay) for delay in range(3)]
    c1 = timeout[0] | timeout[1]
    c2 = c1 | timeout[2]

    def p1(env, condition):
        results = yield condition
        assert results == {timeout[0]: 0}

    def p2(env, condition):
        results = yield condition
        assert results == {timeout[0]: 0}

    env.process(p1(env, c1))
    env.process(p2(env, c2))
    env.run()


def test_condition_value(env):
    """The value of a condition behaves like a readonly dictionary."""
    timeouts = list([env.timeout(delay, value=delay) for delay in range(3)])

    def p(env, timeouts):
        results = yield env.all_of(timeouts)
        assert list(results) == timeouts
        assert list(results.keys()) == timeouts
        assert list(results.values()) == [0, 1, 2]
        assert list(results.items()) == list(zip(timeouts, [0, 1, 2]))
        assert timeouts[0] in results
        assert results[timeouts[0]] == 0
        assert results == results
        assert results == results.todict()

    env.process(p(env, timeouts))
    env.run()


def test_result_order(env):
    """The order of a conditions result is based on the order in which the
    events have been specified."""
    timeouts = list(reversed([env.timeout(delay) for delay in range(3)]))

    def p(env, timeouts):
        results = yield env.all_of(timeouts)
        assert list(results.keys()) == timeouts

    env.process(p(env, timeouts))
    env.run()


def test_nested_result_order(env):
    """The order of a conditions result is based on the order in which the
    events have been specified (even if nested)."""
    timeouts = [env.timeout(delay) for delay in range(3)]
    condition = (timeouts[0] | timeouts[1]) & timeouts[2]

    def p(env, timeouts):
        results = yield condition
        assert list(results.keys()) == timeouts

    env.process(p(env, timeouts))
    env.run()


def test_all_of_empty_list(env):
    """AllOf with an empty list should immediately be triggered."""
    evt = env.all_of([])
    assert evt.triggered


def test_any_of_empty_list(env):
    """AnyOf with an empty list should immediately be triggered."""
    evt = env.any_of([])
    assert evt.triggered
