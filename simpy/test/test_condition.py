from simpy import simulate


# TODO Test behaviour of errors in nested expressions.


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
