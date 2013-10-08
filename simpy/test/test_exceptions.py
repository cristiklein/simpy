"""
Tests for forwarding exceptions from child to parent processes.

"""
import pytest

from simpy import _compat


def test_error_forwarding(env):
    """Exceptions are forwarded from child to parent processes if there
    are any.

    """
    def child(env):
        raise ValueError('Onoes!')
        yield env.timeout(1)

    def parent(env):
        try:
            yield env.process(child(env))
            pytest.fail('We should not have gotten here ...')
        except ValueError as err:
            assert err.args[0] == 'Onoes!'

    env.process(parent(env))
    env.run()


def test_no_parent_process(env):
    """Exceptions should be normally raised if there are no processes waiting
    for the one that raises something.

    """
    def child(env):
        raise ValueError('Onoes!')
        yield env.timeout(1)

    def parent(env):
        try:
            env.process(child(env))
            yield env.timeout(1)
        except Exception as err:
            pytest.fail('There should be no error (%s).' % err)

    env.process(parent(env))
    pytest.raises(ValueError, env.run)


def test_crashing_child_traceback(env):
    def panic(env):
        yield env.timeout(1)
        raise RuntimeError('Oh noes, roflcopter incoming... BOOM!')

    def root(env):
        try:
            yield env.process(panic(env))
            pytest.fail("Hey, where's the roflcopter?")
        except RuntimeError:
            if not _compat.PY2:
                import traceback
                stacktrace = traceback.format_exc()
            else:
                import sys
                stacktrace = ''.join(_compat.format_chain(*sys.exc_info()))

            # The current frame must be visible in the stacktrace.
            assert 'yield env.process(panic(env))' in stacktrace
            assert 'raise RuntimeError(\'Oh noes,' in stacktrace

    env.process(root(env))
    env.run()


@pytest.mark.skipif('sys.version_info[0] < 3')
def test_exception_chaining(env):
    """Unhandled exceptions pass through the entire event stack. This must be
    visible in the stacktrace of the exception.

    """
    def child(env):
        yield env.timeout(1)
        raise RuntimeError('foo')

    def parent(env):
        child_proc = env.process(child(env))
        yield child_proc

    def grandparent(env):
        parent_proc = env.process(parent(env))
        yield parent_proc

    env.process(grandparent(env))
    try:
        env.run()
        pytest.fail('There should have been an exception')
    except RuntimeError:
        import traceback
        trace = traceback.format_exc()
        assert 'raise RuntimeError(\'foo\')' in trace
        assert 'yield child_proc' in trace
        assert 'yield parent_proc' in trace


def test_invalid_event(env):
    """Invalid yield values will cause the simulation to fail."""

    def root(env):
        yield None

    env.process(root(env))
    try:
        env.run()
        pytest.fail('Hey, this is not allowed!')
    except RuntimeError as err:
        assert err.args[0].endswith('Invalid yield value "None"')


def test_exception_handling(env):
    """If failed events are not defused (which is the default) the simulation
    crashes."""

    event = env.event()
    event.fail(RuntimeError())
    try:
        env.run(until=1)
        assert False, 'There must be a RuntimeError!'
    except RuntimeError:
        pass


def test_callback_exception_handling(env):
    """Callbacks of events may handle exception by setting the ``defused``
    attribute of ``event`` to ``True``."""
    def callback(event):
        event.defused = True

    event = env.event()
    event.callbacks.append(callback)
    event.fail(RuntimeError())
    assert not hasattr(event, 'defused'), 'Event has been defused immediately'
    env.run(until=1)
    assert event.defused, 'Event has not been defused'


def test_process_exception_handling(env):
    """Processes can't ignore failed events and auto-handle execeptions."""
    def pem(env, event):
        try:
            yield event
            assert False, 'Hey, the event should fail!'
        except RuntimeError:
            pass

    event = env.event()
    env.process(pem(env, event))
    event.fail(RuntimeError())

    assert not hasattr(event, 'defused'), 'Event has been defuseed immediately'
    env.run(until=1)
    assert event.defused, 'Event has not been defused'
