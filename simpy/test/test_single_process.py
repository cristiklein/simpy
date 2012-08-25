# encoding: utf-8
"""
API tests for single processes (no interaction with other processes or
resources).

"""
# Pytest gets the parameters "sim" and "log" from the *conftest.py* file
import pytest

# from simpy.util import at, delayed


def test_discrete_time_steps(sim, log):
    """Simple simulation with discrete time steps."""
    def pem(context, log):
        while True:
            log.append(context.now)
            yield context.hold(delta_t=1)

    sim.start(pem, log)
    sim.simulate(until=3)

    assert log == [0, 1, 2]


def test_stop_self(sim, log):
    """Process stops itself."""
    def pem(context, log):
        while context.now < 2:
            log.append(context.now)
            yield context.hold(1)

    sim.start(pem, log)
    sim.simulate(10)

    assert log == [0, 1]


@pytest.mark.xfail
def test_start_delayed(sim):
    """The *start* method starts a process at the current time. However,
    there is a helper that lets you delay the start of a process.

    """
    def pem(context):
        assert context.now == 5
        yield context.hold(1)

    sim.start(delayed(delta_t=5), pem)
    sim.simulate()


@pytest.mark.xfail
def test_start_at(sim):
    """The *start* method starts a process at the current time. However,
    there is a helper that lets you start a process at a certain point
    in future.

    """
    def pem(context):
        assert context.now == 5
        yield context.hold(1)

    sim.start(at(t=5), pem)
    sim.simulate()


def test_yield_none_forbidden(sim):
    """A process may not yield ``None``."""
    def pem(context):
        yield

    sim.start(pem)
    pytest.raises(ValueError, sim.simulate)


def test_hold_not_yielded(sim):
    """Check if an error is raised if you forget to yield a hold."""
    def pem(context):
        context.hold(1)
        yield context.hold(1)

        assert context.now == 1

    sim.start(pem)
    pytest.raises(RuntimeError, sim.simulate)


def test_illegal_yield(sim):
    """There should be an error if a process neither yields an event
    nor another process."""
    def pem(context):
        yield 'ohai'

    sim.start(pem)
    pytest.raises(ValueError, sim.simulate)
