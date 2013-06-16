"""
Helpers for real-time (aka *wallclock time*) simulations.

"""
try:
    # Python >= 3.3
    from time import monotonic as time, sleep
except ImportError:
    # Python < 3.3
    from time import time, sleep

from simpy.core import Environment, Scheduler


Infinity = float('inf')


class RealtimeScheduler(Scheduler):
    def __init__(self, env, sim_start, factor, strict):
        Scheduler.__init__(self, env)
        self.sim_start = sim_start
        self.real_start = time()
        self.factor = factor
        self.strict = strict

    def fetch(self):
        event = Scheduler.fetch(self)

        sim_delta = self.now - self.sim_start
        real_delta = time() - self.real_start
        delay = sim_delta * self.factor - real_delta

        if delay > 0:
            sleep(delay)
        elif self.strict and -delay > self.factor:
            # Events scheduled for time *t* may take just up to *t+1*
            # for their computation, before an error is raised.
            raise RuntimeError(
                'Simulation too slow for real time (%.3fs).' % -delay)
        return event


class RealtimeEnvironment(Environment):
    """
    A simulation time step in this environment will take *factor* seconds of
    real time (one second by default), e.g. if you simulate from ``0`` until
    ``3`` with ``factor=0.5``, the call will take at least 1.5 seconds. If the
    processing of the events for a time step takes too long, a
    :exc:`RuntimeError` is raised. You can disable this behavior by setting
    *strict* to ``False``.
    """

    def __init__(self, initial_time=0, factor=1.0, strict=True):
        Environment.__init__(self, initial_time, RealtimeScheduler(
            self, initial_time, factor, strict))
