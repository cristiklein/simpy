"""
API tests for single processes (no interaction with other processes or
resources).

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import pytest

from simpy import simulate


def test_discrete_time_steps(env, log):
    """envple envulation with discrete time steps."""
    def pem(context, log):
        while True:
            log.append(context.now)
            yield context.hold(delta_t=1)

    env.start(pem(env, log))
    simulate(env, until=3)

    assert log == [0, 1, 2]


def test_stop_self(env, log):
    """Process stops itself."""
    def pem(context, log):
        while context.now < 2:
            log.append(context.now)
            yield context.hold(1)

    env.start(pem(env, log))
    simulate(env, 10)

    assert log == [0, 1]


def test_start_at(env):
    def pem(context):
        assert context.now == 5
        yield context.hold(1)

    env.start(pem(env), at=5)
    simulate(env)


def test_start_at_error(env):
    def pem(context):
        yield context.hold(2)

    env.start(pem(env))
    simulate(env)
    pytest.raises(ValueError, env.start, pem(env), at=1)


def test_start_delayed(env):
    def pem(context):
        assert context.now == 5
        yield context.hold(1)

    env.start(pem(env), delay=5)
    simulate(env)


def test_start_delayed_error(env):
    """Check if delayed() raises an error if you pass a negative dt."""
    def pem(context):
        yield context.hold(1)

    pytest.raises(ValueError, env.start, pem(env), delay=-1)


def test_start_at_delay_precedence(env):
    """The ``delay`` param shoul take precedence ofer the ``at`` param."""
    def pem(context):
        assert context.now == 5
        yield context.hold(1)

    env.start(pem(env), at=3, delay=5)
    simulate(env)


def test_start_non_process(env):
    """Check that you cannot start a normal function."""
    def foo():
        pass

    pytest.raises(ValueError, env.start, foo)


def test_negative_hold(env):
    """Don't allow negative hold times."""
    def pem(context):
        yield context.hold(-1)

    env.start(pem(env))
    pytest.raises(ValueError, simulate, env)


def test_yield_none_forbidden(env):
    """A process may not yield ``None``."""
    def pem(context):
        yield

    env.start(pem(env))
    pytest.raises(ValueError, simulate, env)


def test_hold_not_yielded(env):
    """Check if an error is raised if you forget to yield a hold."""
    def pem(context):
        context.hold(1)
        yield context.hold(1)

    env.start(pem(env))
    pytest.raises(RuntimeError, simulate, env)


def test_illegal_yield(env):
    """There should be an error if a process neither yields an event
    nor another process."""
    def pem(context):
        yield 'ohai'

    env.start(pem(env))
    pytest.raises(ValueError, simulate, env)


def test_get_process_state(env):
    """A process is alive until it's generator has not terminated."""
    def pem_a(context):
        yield context.hold(3)

    def pem_b(context, pem_a):
        yield context.hold(1)
        assert pem_a.is_alive

        yield context.hold(3)
        assert not pem_a.is_alive

    proc_a = env.start(pem_a(env))
    env.start(pem_b(env, proc_a))
    simulate(env)


def test_simulate_negative_until(env):
    """Test passing a negative time to simulate."""
    pytest.raises(ValueError, simulate, env, -3)


def test_hold_value(env):
    """You can pass an additional *value* to *hold* which will be
    directly yielded back into the PEM. This is useful to implement some
    kinds of resources or other additions.

    See :class:`envpy.resources.Store` for an example.

    """
    def pem(context):
        val = yield context.hold(1, 'ohai')
        assert val == 'ohai'

    env.start(pem(env))
    simulate(env)
