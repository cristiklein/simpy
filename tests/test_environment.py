"""
General test for the the `simpy.core.Environment`.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import pytest


def test_event_queue_empty(env, log):
    """The simulation should stop if there are no more events, that means, no
    more active process."""
    def pem(env, log):
        while env.now < 2:
            log.append(env.now)
            yield env.timeout(1)

    env.process(pem(env, log))
    env.run(10)

    assert log == [0, 1]


def test_run_negative_until(env):
    """Test passing a negative time to run."""
    pytest.raises(ValueError, env.run, -3)


def test_run_resume(env):
    """Stopped simulation can be resumed."""
    events = [env.timeout(t) for t in (5, 10, 15)]

    assert env.now == 0
    assert not any(event.processed for event in events)

    env.run(until=10)
    assert env.now == 10
    assert all(event.processed for event in events[:1])
    assert not any(event.processed for event in events[1:])

    env.run(until=15)
    assert env.now == 15
    assert all(event.processed for event in events[:2])
    assert not any(event.processed for event in events[2:])

    env.run()
    assert env.now == 15
    assert all(event.processed for event in events)


def test_run_until_value(env):
    """Anything that can be converted to a float is a valid until value."""
    env.run(until='3.141592')
    assert env.now == 3.141592


def test_run_with_processed_event(env):
    """An already processed event may also be passed as until value."""
    timeout = env.timeout(1, value='spam')
    assert env.run(until=timeout) == 'spam'
    assert env.now == 1

    # timeout has been processed, calling run again will return its value
    # again.

    assert env.run(until=timeout) == 'spam'
    assert env.now == 1


def test_run_with_untriggered_event(env):
    excinfo = pytest.raises(RuntimeError, env.run, until=env.event())
    assert str(excinfo.value).startswith('No scheduled events left but "until"'
                                         ' event was not triggered:')
