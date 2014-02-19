"""
Tests for Simpy's real-time behavior.

"""
import time
try:
    # Python >= 3.3
    from time import monotonic
except ImportError:
    # Python < 3.3
    from time import time as monotonic

import pytest

from simpy.rt import RealtimeEnvironment


def process(env, log, sleep, timeout=1):
    """Test process."""
    while True:
        time.sleep(sleep)
        yield env.timeout(timeout)
        log.append(env.now)


def check_duration(real, expected):
    return expected <= real < (expected + 0.02)


@pytest.mark.parametrize('factor', [0.1, 0.05, 0.15])
def test_rt(log, factor):
    """Basic tests for run()."""
    env = RealtimeEnvironment(factor=factor)
    env.process(process(env, log, 0.01, 1))
    env.process(process(env, log, 0.02, 1))

    start = monotonic()
    env.run(2)
    duration = monotonic() - start

    assert check_duration(duration, 2 * factor)
    assert log == [1, 1]


def test_rt_multiple_call(log):
    """Test multiple calls to run()."""
    env = RealtimeEnvironment(factor=0.05)
    start = monotonic()

    env.process(process(env, log, 0.01, 2))
    env.process(process(env, log, 0.01, 3))

    env.run(5)
    duration = monotonic() - start

    # assert almost_equal(duration, 0.2)
    assert check_duration(duration, 5 * 0.05)
    assert log == [2, 3, 4]

    env.run(12)
    duration = monotonic() - start

    assert check_duration(duration, 12 * 0.05)
    assert log == [2, 3, 4, 6, 6, 8, 9, 10]


def test_rt_slow_sim_default_behavior(log):
    """By default, SimPy should raise an error if a simulation is too
    slow for the selected real-time factor."""
    env = RealtimeEnvironment(factor=0.05)
    env.process(process(env, log, 0.1, 1))

    err = pytest.raises(RuntimeError, env.run, 3)
    assert 'Simulation too slow for real time' in err.value.args[0]
    assert log == []


def test_rt_slow_sim_no_error(log):
    """Test ignoring slow simulations."""
    env = RealtimeEnvironment(factor=0.05, strict=False)
    env.process(process(env, log, 0.1, 1))

    start = monotonic()
    env.run(2)
    duration = monotonic() - start

    assert check_duration(duration, 2 * 0.1)
    assert log == [1]


def test_rt_illegal_until():
    """Test illegal value for *until*."""
    env = RealtimeEnvironment()
    err = pytest.raises(ValueError, env.run, -1)
    assert err.value.args[0] == ('until(=-1.0) should be > the current '
                                 'simulation time.')
