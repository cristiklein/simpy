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
    """This :class:`~simpy.core.Scheduler` delays the :meth:`pop()` operation
    to adjust to the wallclock time.

    The arguments *env* and an *initial_time* are passed to
    :class:`~simpy.core.Scheduler`.

    A simulation time step will take *factor* seconds of real time (one second
    by default), e.g. if you simulate from ``0`` until ``3`` with
    ``factor=0.5``, the :meth:`~simpy.core.Environment.simulate()` call will
    take at least 1.5 seconds.

    If the processing of the events for a time step takes too long,
    a :exc:`RuntimeError` is raised by :meth:`pop()`. You can disable this
    behavior by setting *strict* to ``False``.

    """
    def __init__(self, env, initial_time, factor=1.0, strict=True):
        Scheduler.__init__(self, env, initial_time)
        self.sim_start = initial_time
        self.real_start = time()
        self.factor = factor
        self.strict = strict

    def pop(self):
        """Return the next event from the schedule.

        The call is delayed corresponding to the real-time *factor* of the
        scheduler.

        If the events of a simulation time step are processed to slowly for the
        given *factor* and if *strict* is enabled, raise a :exc:`RuntimeError`.

        """
        event = super(RealtimeScheduler, self).pop()

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
    """This :class:`~simpy.core.Environment` uses a :class:`RealtimeScheduler`
    by default, so a simulation time step will take *factor* seconds of real
    time (see :class:`RealtimeScheduler` for more information).

    """
    def __init__(self, initial_time=0, factor=1.0, strict=True):
        Environment.__init__(self, initial_time, RealtimeScheduler(
            self, initial_time, factor, strict))
