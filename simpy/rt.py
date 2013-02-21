"""
Helpers for real-time (aka *wallclock time*) simulations.

"""
from numbers import Number
try:
    # Python >= 3.3
    from time import monotonic as time, sleep
except ImportError:
    # Python < 3.3
    from time import time, sleep

from simpy.core import Event, step, EVT_INIT, SUCCEED


Infinity = float('inf')


def simulate(env, until=Infinity, factor=1.0, strict=True):
    """Simulate the environment until the given criterion *until* is met.

    A simulation time step will take *factor* seconds of real time (one
    second by default), e.g. if you simulate from ``0`` until ``3`` with
    ``factor=0.5``, the call will take at least 1.5 seconds. If the
    processing of the events for a time step takes to long,
    a :exc:`RuntimeError` is raised. You can disable this behavior by
    setting *strict* to ``False``.

    The parameter ``until`` specifies when the simulation ends.

    - If it is ``None`` (which is the default) the simulation will only
      stop if there are no further events.

    - If it is an :class:`Event` the simulation will stop once this
      event has happened.

    - If it is a number the simulation will stop when the simulation
      time reaches *until*. (*Note:* Internally, a :class:`Timeout`
      event is created, so the simulation time will be exactly *until*
      afterwards (as it is ``0`` at the beginning)).

    """
    if until is None:
        until = env.event()
    elif isinstance(until, Number):
        if until <= env.now:
            raise ValueError('until(=%s) should be > the current simulation '
                             'time.' % until)
        delay = until - env.now
        until = env.event()
        # EVT_INIT schedules "until" before all other events for that time.
        env._schedule(EVT_INIT, until, SUCCEED, delay=delay)
    elif not isinstance(until, Event):
        raise ValueError('"until" must be None, a number or an event, '
                         'but not "%s"' % until)

    events = env._events
    start_rt = time()
    start_st = env.now
    while events and until.callbacks is not None:
        evt_time = events[0][0]
        st_delta = evt_time - start_st  # Sim time from start to next event
        rt_delta = time() - start_rt   # Time already passed from start
        sleep_dur = st_delta * factor - rt_delta  # Time left to wait

        if sleep_dur > 0:
            sleep(sleep_dur)
        elif strict and -sleep_dur > factor:
            # Events scheduled for time *t* may take just up to *t+1*
            # for their computation, before an error is raised.
            raise RuntimeError('Simulation too slow for real time (%.3fs).' %
                               -sleep_dur)

        step(env)
