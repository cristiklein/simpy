"""
API tests for single processes (no interaction with other processes or
resources).

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import re

import pytest

from simpy.events import Process


def test_discrete_time_steps(env, log):
    """envple envulation with discrete time steps."""
    def pem(env, log):
        while True:
            log.append(env.now)
            yield env.timeout(delay=1)

    env.start(pem(env, log))
    env.run(until=3)

    assert log == [0, 1, 2]


def test_stop_self(env, log):
    """Process stops itself."""
    def pem(env, log):
        while env.now < 2:
            log.append(env.now)
            yield env.timeout(1)

    env.start(pem(env, log))
    env.run(10)

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
    pytest.raises(ValueError, env.run)


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
    env.run()


def test_run_negative_until(env):
    """Test passing a negative time to run."""
    pytest.raises(ValueError, env.run, -3)


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
    env.run()


def test_event_succeeds(env):
    """Test for the Environment.event() helper function."""
    def child(env, event):
        value = yield event
        assert value == 'ohai'
        assert env.now == 5

    def parent(env):
        event = env.event()
        env.start(child(env, event))
        yield env.timeout(5)
        event.succeed('ohai')

    env.start(parent(env))
    env.run()


def test_event_fails(env):
    """Test for the Environment.event() helper function."""
    def child(env, event):
        try:
            yield event
            pytest.fail('Should not get here.')
        except ValueError as err:
            assert err.args[0] == 'ohai'
            assert env.now == 5

    def parent(env):
        event = env.event()
        env.start(child(env, event))
        yield env.timeout(5)
        event.fail(ValueError('ohai'))

    env.start(parent(env))
    env.run()


def test_exit_with_process(env):
    def child(env, fork):
        env.exit(env.start(child(env, False)) if fork else None)
        yield

    def parent(env):
        result = yield env.start(child(env, True))

        assert type(result) is Process

    env.start(parent(env))
    env.run()


def test_shared_timeout(env, log):
    def child(env, timeout, id, log):
        yield timeout
        log.append((id, env.now))

    timeout = env.timeout(1)
    for i in range(3):
        env.start(child(env, timeout, i, log))

    env.run()
    assert log == [(0, 1), (1, 1), (2, 1)]


def test_process_target(env):
    def pem(env, event):
        yield event

    event = env.timeout(5)
    proc = env.start(pem(env, event))

    # Wait until "proc" is initialized and yielded the event
    while env.peek() < 5:
        env.step()
    assert proc.target is event
    proc.interrupt()


def test_run_resume(env):
    """Stopped simulation can be resumed."""
    events = [env.timeout(t) for t in (5, 10, 15)]

    env.run(until=10)
    assert events[0].processed
    assert not events[1].processed
    assert not events[2].processed
    assert env.now == 10

    env.run(until=15)
    assert events[1].processed
    assert not events[2].processed
    assert env.now == 15

    env.run()
    assert events[2].processed
    assert env.now == 15


def test_run_until_value(env):
    """Anything that can be converted to a float is a valid until value."""
    env.run(until='3.141592')
    assert env.now == 3.141592


def test_names(env):
    def pem():
        yield env.exit()

    assert re.match(r'<Event\(\) object at 0x.*>', str(env.event()))

    assert re.match(r'<Timeout\(1\) object at 0x.*>', str(env.timeout(1)))
    assert re.match(r'<Timeout\(1, value=2\) object at 0x.*>',
                    str(env.timeout(1, value=2)))

    assert re.match(r'<Condition\(all_events, \[<Event\(\) object at 0x.*>, '
                    r'<Event\(\) object at 0x.*>\]\) object at 0x.*>',
                    str(env.event() & env.event()))

    assert re.match(r'<Process\(pem\) object at 0x.*>', str(env.start(pem())))


def test_event_value(env):
    """After an event has been triggered, its value becomes accessible."""
    event = env.timeout(0, 'I am the value')

    env.run()

    assert event.value == 'I am the value'


def test_unavailable_event_value(env):
    """If an event has not yet been triggered, its value is not availabe and
    trying to access it will result in a RuntimeError."""
    event = env.event()

    try:
        event.value
        assert False, 'Expected an exception'
    except RuntimeError as e:
        assert e.args[0].endswith('is not yet available')


def test_triggered_event(env):
    def pem(env, event):
        value = yield event
        env.exit(value)

    event = env.event()
    event.succeed('i was already done')

    result = env.run(env.start(pem(env, event)))

    assert result == 'i was already done'


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

    env.run(env.start(process(env)))
