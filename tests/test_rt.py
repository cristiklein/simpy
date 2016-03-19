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
    start = monotonic()
    env = RealtimeEnvironment(factor=factor)
    env.process(process(env, log, 0.01, 1))
    env.process(process(env, log, 0.02, 1))

    env.run(2)
    duration = monotonic() - start

    assert check_duration(duration, 2 * factor)
    assert log == [1, 1]


def test_rt_multiple_call(log):
    """Test multiple calls to run()."""
    start = monotonic()
    env = RealtimeEnvironment(factor=0.05)

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
    assert 'Simulation too slow for real time' in str(err.value)
    assert log == []


def test_rt_slow_sim_no_error(log):
    """Test ignoring slow simulations."""
    start = monotonic()
    env = RealtimeEnvironment(factor=0.05, strict=False)
    env.process(process(env, log, 0.1, 1))

    env.run(2)
    duration = monotonic() - start

    assert check_duration(duration, 2 * 0.1)
    assert log == [1]


def test_rt_illegal_until():
    """Test illegal value for *until*."""
    env = RealtimeEnvironment()
    err = pytest.raises(ValueError, env.run, -1)
    assert str(err.value) == ('until(=-1.0) should be > the current '
                              'simulation time.')


def test_rt_sync(log):
    """Test resetting the internal wall-clock reference time."""
    env = RealtimeEnvironment(factor=0.05)
    env.process(process(env, log, 0.01))
    time.sleep(0.06)  # Simulate massiv workload :-)
    env.sync()
    env.run(3)


def test_run_with_untriggered_event(env):
    env = RealtimeEnvironment(factor=0.05)
    excinfo = pytest.raises(RuntimeError, env.run, until=env.event())
    assert str(excinfo.value).startswith('No scheduled events left but "until"'
                                         ' event was not triggered:')
