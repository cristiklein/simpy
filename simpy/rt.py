"""
Helpers for real-time (aka *wallclock time*) simulations.

"""
try:
    # Python >= 3.3
    from time import monotonic as time, sleep
except ImportError:
    # Python < 3.3
    from time import time, sleep

from simpy.core import step


Infinity = float('inf')


def simulate(env, until=Infinity, factor=1.0, strict=True):
    if until <= 0:
        raise ValueError('until(=%s) should be a number > 0.' % until)

    events = env._events
    start_rt = time()
    start_st = env.now
    while events and events[0][0] < until:
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
