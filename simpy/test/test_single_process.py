"""
API tests for single processes (no interaction with other processes or
resources).

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import pytest

from simpy import simulate


def test_discrete_time_steps(env, log):
    """envple envulation with discrete time steps."""
    def pem(env, log):
        while True:
            log.append(env.now)
            yield env.timeout(delay=1)

    env.start(pem(env, log))
    simulate(env, until=3)

    assert log == [0, 1, 2]


def test_stop_self(env, log):
    """Process stops itself."""
    def pem(env, log):
        while env.now < 2:
            log.append(env.now)
            yield env.timeout(1)

    env.start(pem(env, log))
    simulate(env, 10)

    assert log == [0, 1]


def test_start_non_process(env):
    """Check that you cannot start a normal function."""
    def foo():
        pass

    pytest.raises(ValueError, env.start, foo)


def test_negative_timeout(env):
    """Don't allow negative timeout times."""
    def pem(env):
        yield env.timeout(-1)

    env.start(pem(env))
    pytest.raises(ValueError, simulate, env)


def test_yield_none_forbidden(env):
    """A process may not yield ``None``."""
    def pem(env):
        yield

    env.start(pem(env))
    pytest.raises(ValueError, simulate, env)


def test_illegal_yield(env):
    """There should be an error if a process neither yields an event
    nor another process."""
    def pem(env):
        yield 'ohai'

    env.start(pem(env))
    pytest.raises(ValueError, simulate, env)


def test_get_process_state(env):
    """A process is alive until it's generator has not terminated."""
    def pem_a(env):
        yield env.timeout(3)

    def pem_b(env, pem_a):
        yield env.timeout(1)
        assert pem_a.is_alive

        yield env.timeout(3)
        assert not pem_a.is_alive

    proc_a = env.start(pem_a(env))
    env.start(pem_b(env, proc_a))
    simulate(env)


def test_simulate_negative_until(env):
    """Test passing a negative time to simulate."""
    pytest.raises(ValueError, simulate, env, -3)


def test_timeout_value(env):
    """You can pass an additional *value* to *timeout* which will be
    directly yielded back into the PEM. This is useful to implement some
    kinds of resources or other additions.

    See :class:`envpy.resources.Store` for an example.

    """
    def pem(env):
        val = yield env.timeout(1, 'ohai')
        assert val == 'ohai'

    env.start(pem(env))
    simulate(env)
