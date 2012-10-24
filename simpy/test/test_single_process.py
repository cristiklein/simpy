# encoding: utf-8
"""
API tests for single processes (no interaction with other processes or
resources).

"""
# Pytest gets the parameters "sim" and "log" from the *conftest.py* file
import pytest

# from simpy.util import at, delayed


def test_discrete_time_steps(ctx):
    """Simple simulation with discrete time steps."""
    def pem(ctx, log):
        while True:
            log.append(ctx.now)
            yield ctx.wait(1)

    log = []
    ctx.start(pem(ctx, log))
    yield ctx.wait(3)
    assert log == [0, 1, 2]


def test_stop_self(ctx):
    """Process stops itself."""
    def pem(ctx, log):
        while ctx.now < 2:
            log.append(ctx.now)
            yield ctx.wait(1)

    log = []
    yield ctx.start(pem(ctx, log))
    assert log == [0, 1]


@pytest.mark.xfail
def test_start_delayed(sim):
    """The *start* method starts a process at the current time. However,
    there is a helper that lets you delay the start of a process.

    """
    def pem(ctx):
        assert ctx.now == 5
        yield ctx.wait(1)

    sim.start(delayed(delta_t=5), pem)
    sim.simulate()


@pytest.mark.xfail
def test_start_at(sim):
    """The *start* method starts a process at the current time. However,
    there is a helper that lets you start a process at a certain point
    in future.

    """
    def pem(ctx):
        assert ctx.now == 5
        yield ctx.wait(1)

    sim.start(at(t=5), pem)
    sim.simulate()


@pytest.mark.xfail
def test_yield_none_forbidden(sim):
    """A process may not yield ``None``."""
    def pem(ctx):
        yield

    sim.start(pem)
    pytest.raises(ValueError, sim.simulate)
