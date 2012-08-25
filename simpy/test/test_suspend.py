"""
Tests for suspend/resume.

"""
import pytest


def test_suspend_resume(sim):
    """If a process passivates itself, it will no longer get active by
    itself but needs to be reactivated by another process (in contrast
    to interrupts, where the interrupt may or may not occur).

    """
    def sleeper(context):
        yield context.suspend()
        assert context.now == 10

    def alarm(context, sleeper):
        yield context.hold(10)
        context.resume(sleeper)

    sleeper = sim.start(sleeper)
    sim.start(alarm, sleeper)
    sim.simulate()


def test_illegal_suspend(sim):
    """Deny suspension if a process forgot to yield a "hold()"."""
    def pem(context):
        context.hold(1)
        yield context.suspend()

    sim.start(pem)
    pytest.raises(RuntimeError, sim.simulate)


def test_resume_before_start(sim):
    """A process must be started before any there can be any interaction.

    As a consequence you can't resume or interrupt a just started
    process as shown in this test. See :func:`test_immediate_resume` for
    the correct way to immediately resume a started process.

    """
    def child(ctx):
        yield ctx.hold(1)

    def root(ctx):
        c = ctx.start(child)
        ctx.resume(c)
        yield ctx.hold(1)

    try:
        sim.start(root)
        sim.simulate()
        pytest.fail()
    except RuntimeError as exc:
        assert exc.args[0] == 'Process(1, child) is not suspended.'


def test_immediate_resume(sim, log):
    """Check if a process can immediately be resumed."""
    def sleeper(context, log):
        yield context.suspend()
        log.append(context.now)

    def waker(context, sleeper_proc):
        context.resume(sleeper_proc)
        yield context.hold()

    sleeper_proc = sim.start(sleeper, log)
    sim.start(waker, sleeper_proc)
    sim.simulate()

    assert log == [0]
