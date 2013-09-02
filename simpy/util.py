"""
This modules contains various utility functions:

- :func:`start_delayed()`: Start a process with a given delay.
- :func:`subscribe_at()`: Receive an interrupt if an event occurs.

"""
from simpy.core import Condition


def start_delayed(env, peg, delay):
    """Return a helper process that starts another PEM after a delay of
    ``delay``.

    :meth:`~simpy.core.Environment.start` starts a PEM at the current
    simulation time. This helper allows you to start a PEM after a delay
    of ``delay`` simulation time units.

    Just pass it as a first parameter to ``start()``::

        >>> from simpy import Environment, simulate
        >>> from simpy.util import start_delayed
        >>> def pem(env, x):
        ...     print('%s, %s' % (env.now, x))
        ...     yield env.timeout(1)
        ...
        >>> env = Environment()
        >>> proc = start_delayed(env, pem(env, 3), 5)
        >>> simulate(env)
        5, 3

    Raises a :exc:`ValueError` if ``delay <= 0``.

    """
    if delay <= 0:
        raise ValueError('delay(=%s) must be > 0.' % delay)

    def starter():
        yield env.timeout(delay)
        proc = env.start(peg)
        env.exit(proc)

    return env.start(starter())


def subscribe_at(event):
    """Register at the ``event`` to receive an interrupt when it occurs.

    The most common use case for this is to pass
    a :class:`~simpy.core.Process` to get notified when it terminates.

    Raise a :exc:`RuntimeError` if ``event`` has already occurred.

    """
    env = event.env
    subscriber = env.active_process

    def signaller(signaller, receiver):
        result = yield signaller
        if receiver.is_alive:
            receiver.interrupt((signaller, result))

    if event.callbacks is not None:
        env.start(signaller(event, subscriber))
    else:
        raise RuntimeError('%s has already terminated.' % event)
