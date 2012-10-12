"""
Tests for suspend/resume.

"""
import pytest

from simpy import simulate


def test_suspend_resume(env):
    """If a process passivates itself, it will no longer get active by
    itself but needs to be reactivated by another process (in contrast
    to interrupts, where the interrupt may or may not occur).

    """
    def sleeper(env):
        yield env.suspend()
        assert env.now == 10

    def alarm(env, sleeper):
        yield env.hold(10)
        sleeper.resume()

    sleeper = env.start(sleeper(env))
    env.start(alarm(env, sleeper))
    simulate(env)


def test_illegal_suspend(env):
    """Deny suspension if a process forgot to yield a "hold()"."""
    def pem(env):
        env.hold(1)
        yield env.suspend()

    env.start(pem(env))
    pytest.raises(RuntimeError, simulate, env)


def test_resume_before_start(env):
    """A process must be started before any there can be any interaction.

    As a consequence you can't resume or interrupt a just started
    process as shown in this test. See :func:`test_immediate_resume` for
    the correct way to immediately resume a started process.

    """
    def child(env):
        yield env.hold(1)

    def root(env):
        c = env.start(child(env))
        c.resume()
        yield env.hold(1)

    try:
        env.start(root(env))
        simulate(env)
        pytest.fail()
    except RuntimeError as exc:
        assert exc.args[0] == 'Process(child) is not suspended.'


def test_immediate_resume(env, log):
    """Check if a process can immediately be resumed."""
    def sleeper(env, log):
        yield env.suspend()
        log.append(env.now)

    def waker(env, sleeper_proc):
        sleeper_proc.resume()
        yield env.hold()

    sleeper_proc = env.start(sleeper(env, log))
    env.start(waker(env, sleeper_proc))
    simulate(env)

    assert log == [0]


def test_resume_value(env):
    """You can pass an additional *value* to *resume* which will be
    yielded back into the PEM of the resumed process. This is useful to
    implement some kinds of resources or other additions.

    See :class:`simpy.resources.Store` for an example.

    """
    def child(env, expected):
        value = yield env.suspend()
        assert value == expected

    def parent(env, value):
        child_proc = env.start(child(env, value))
        yield env.hold(1)
        child_proc.resume(value)

    env.start(parent(env, 'ohai'))
    simulate(env)
