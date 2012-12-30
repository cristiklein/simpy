import pytest

from simpy import simulate


# TODO Test behaviour of errors in nested expressions.


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
                timeout[1]: 1,
                timeout[2]: 2,
        }
        assert env.now == 2

    env.start(process(env))
    simulate(env)


def test_nested_cond_with_error(env):
    def explode(env):
        yield env.timeout(1)
        raise ValueError('Onoes!')

    def process(env):
        try:
            yield env.start(explode(env)) & env.timeout(1)
            pytest.fail('The yield should have raised a ValueError')
        except ValueError as err:
            assert err.args == ('Onoes!',)

    env.start(process(env))
    simulate(env)


def test_cond_with_uncaught_error(env):
    def explode(env):
        yield env.timeout(1)
        raise ValueError('Onoes!')

    def process(env):
            yield env.start(explode(env)) & env.timeout(1)
            pytest.fail('The yield should have raised a ValueError')

    env.start(process(env))
    err = pytest.raises(ValueError, simulate, env)
    assert err.value.args == ('Onoes!',)


def test_iand_with_and_cond(env):
    def process(env):
        cond = env.timeout(1, value=1) & env.timeout(2, value=2)
        orig = cond

        cond &= env.timeout(0, value=0)
        assert cond is orig

        results = yield cond
        assert sorted(results.values()) == [0, 1, 2]

    env.start(process(env))
    simulate(env)


def test_iand_with_or_cond(env):
    def process(env):
        cond = env.timeout(1, value=1) | env.timeout(2, value=2)
        orig = cond

        cond &= env.timeout(0, value=0)
        assert cond is not orig

        results = yield cond
        assert sorted(results.values()) == [0, 1]

    env.start(process(env))
    simulate(env)


def test_ior_with_or_cond(env):
    def process(env):
        cond = env.timeout(1, value=1) | env.timeout(2, value=2)
        orig = cond

        cond |= env.timeout(0, value=0)
        assert cond is orig

        results = yield cond
        assert sorted(results.values()) == [0]

    env.start(process(env))
    simulate(env)


def test_ior_with_and_cond(env):
    def process(env):
        cond = env.timeout(1, value=1) & env.timeout(2, value=2)
        orig = cond

        cond |= env.timeout(0, value=0)
        assert cond is not orig

        results = yield cond
        assert sorted(results.values()) == [0]

    env.start(process(env))
    simulate(env)


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
        assert results == {timeout[0]: 0, timeout[1]: 1, timeout[2]: 2}

    env.start(p1(env, c1))
    env.start(p2(env, c2))
    simulate(env)
