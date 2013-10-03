"""
Tests for ``simpy.events.Event``.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import re


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
    trying to access it will result in a AttributeError."""
    event = env.event()

    try:
        event.value
        assert False, 'Expected an exception'
    except AttributeError as e:
        assert e.args[0].endswith('is not yet available')


def test_triggered_event(env):
    def pem(env, event):
        value = yield event
        env.exit(value)

    event = env.event()
    event.succeed('i was already done')

    result = env.run(env.start(pem(env, event)))

    assert result == 'i was already done'
