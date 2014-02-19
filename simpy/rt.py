"""Provides an environment whose time passes according to the (scaled)
real-time (aka *wallclock time*)."""

try:
    # Python >= 3.3
    from time import monotonic as time, sleep
except ImportError:
    # Python < 3.3
    from time import time, sleep

from simpy.core import Environment, EmptySchedule, Infinity


class RealtimeEnvironment(Environment):
    """An :class:`~simpy.core.Environment` which uses the real (e.g. wallclock)
    time.

    A time step will take *factor* seconds of real time (one second by
    default); e.g., if you step from ``0`` until ``3`` with ``factor=0.5``, the
    :meth:`simpy.core.BaseEnvironment.run()` call will take at least 1.5
    seconds.

    If the processing of the events for a time step takes too long,
    a :exc:`RuntimeError` is raised in :meth:`step()`. You can disable this
    behavior by setting *strict* to ``False``.

    """
    def __init__(self, initial_time=0, factor=1.0, strict=True):
        Environment.__init__(self, initial_time)

        self.env_start = initial_time
        self.real_start = time()
        self.factor = factor
        """Scaling factor of the real-time."""
        self.strict = strict
        """Running mode of the environment. :meth:`step()` will raise a
        :exc:`RuntimeError` if this is set to ``True`` and the processing of
        events takes too long."""

    def step(self):
        """Waits until enough real-time has passed for the next event to
        happen.

        The delay is scaled according to the real-time :attr:`factor`. If the
        events of a time step are processed too slowly for the given
        :attr:`factor` and if :attr:`strict` is enabled, a :exc:`RuntimeError`
        is raised.

        """
        evt_time = self.peek()

        if evt_time is Infinity:
            raise EmptySchedule()

        real_time = self.real_start + (evt_time - self.env_start) * self.factor

        if self.strict and time() - real_time > self.factor:
            # Events scheduled for time *t* may take just up to *t+1*
            # for their computation, before an error is raised.
            raise RuntimeError(
                'Simulation too slow for real time (%.3fs).' % (
                        time() - real_time))

        # Sleep in a loop to fix inaccuracies of windows (see
        # http://stackoverflow.com/a/15967564 for details) and to ignore
        # interrupts.
        while True:
            delta = real_time - time()
            if delta <= 0:
                break
            sleep(delta)

        return Environment.step(self)
