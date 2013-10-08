"""
Tests for ``simpy.events.Timeout``.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import pytest


def test_discrete_time_steps(env, log):
    """envple envulation with discrete time steps."""
    def pem(env, log):
        while True:
            log.append(env.now)
            yield env.timeout(delay=1)

    env.process(pem(env, log))
    env.run(until=3)

    assert log == [0, 1, 2]


def test_negative_timeout(env):
    """Don't allow negative timeout times."""
    def pem(env):
        yield env.timeout(-1)

    env.process(pem(env))
    pytest.raises(ValueError, env.run)


def test_timeout_value(env):
    """You can pass an additional *value* to *timeout* which will be
    directly yielded back into the PEM. This is useful to implement some
    kinds of resources or other additions.

    See :class:`envpy.resources.Store` for an example.

    """
    def pem(env):
        val = yield env.timeout(1, 'ohai')
        assert val == 'ohai'

    env.process(pem(env))
    env.run()


def test_shared_timeout(env, log):
    def child(env, timeout, id, log):
        yield timeout
        log.append((id, env.now))

    timeout = env.timeout(1)
    for i in range(3):
        env.process(child(env, timeout, i, log))

    env.run()
    assert log == [(0, 1), (1, 1), (2, 1)]


def test_triggered_timeout(env):
    def process(env):
        def child(env, event):
            value = yield event
            env.exit(value)

        event = env.timeout(1, 'i was already done')
        # Start the child after the timeout has already happened.
        yield env.timeout(2)
        value = yield env.process(child(env, event))
        assert value == 'i was already done'

    env.run(env.process(process(env)))
