"""
Tests for forwarding exceptions from child to parent processes.

"""
import pytest

import simpy


def test_error_forwarding(env):
    """Exceptions are forwarded from child to parent processes if there
    are any.

    """
    def child(env):
        raise ValueError('Onoes!')
        yield env.timeout(1)

    def parent(env):
        try:
            yield env.start(child(env))
            pytest.fail('We should not have gotten here ...')
        except ValueError as err:
            assert err.args[0] == 'Onoes!'

    env.start(parent(env))
    simpy.simulate(env)


def test_no_parent_process(env):
    """Exceptions should be normally raised if there are no processes
    waiting for the one that raises something.

    """
    def child(env):
        raise ValueError('Onoes!')
        yield env.timeout(1)

    def parent(env):
        try:
            env.start(child(env))
            yield env.timeout(1)
        except Exception as err:
            pytest.fail('There should be no error (%s).' % err)

    env.start(parent(env))
    pytest.raises(ValueError, simpy.simulate, env)


def test_crashing_child_traceback(env):
    def panic(env):
        yield env.timeout(1)
        raise RuntimeError('Oh noes, roflcopter incoming... BOOM!')

    def root(env):
        try:
            yield env.start(panic(env))
            pytest.fail("Hey, where's the roflcopter?")
        except RuntimeError:
            import traceback
            stacktrace = traceback.format_exc()
            # The current frame must be visible in the stacktrace.
            assert 'yield env.start(panic(env))' in stacktrace

    env.start(root(env))
    simpy.simulate(env)
