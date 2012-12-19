"""
This modules contains various utility functions:

- :func:`subscribe_at`: Receive an interrupt if a process terminates.
- :func:`wait_for_all`: Wait until all passed processes have terminated.
- :func:`wait_for_any`: Wait until one of the passed processes has
  terminated.

"""
from simpy.core import Interrupt


def start_delayed(env, peg, delay):
    """Return a helper process that starts another PEM after a delay of
    ``delay``.

    :meth:`~simpy.core.Environment.start` starts a PEM at the current
    simulation time. This helper allows you to start a PEM after a delay
    of ``delay`` simulation time units.

    Just pass it as a first parameter to ``start()``::

        >>> def pem(env, x):
        ...     print('%s, %s' % (env.now, x))
        ...     yield env.timeout(1)
        ...
        >>> env = Environment()
        >>> start_delayed(env, pem(env, 3), 5)
        Process(starter)
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


def wait_for_all(events):
    """Return a process that waits for all ``events``.

    The result of the helper process will be a list with the results
    of ``events`` in their respective order. The results are either
    the values that can be passed to an event or the return value of a
    :class:`~simpy.core.Process`.

    Raise a :exc:`ValueError` if no events are passed.

    """
    if not events:
        raise ValueError('No processes were passed.')

    env = events[0].env

    def waiter():
        # We cannot simply wait for each process because they might
        # terminate in random order which may cause us to wait for an
        # already terminated process.
        for proc in list(events):
            subscribe_at(proc)

        results = []
        while len(results) < len(events):
            try:
                yield env.suspend()
            except Interrupt as interrupt:
                finished_proc, result = interrupt.cause
                results.append(result)

        env.exit(results)

    return env.start(waiter())


def wait_for_any(events):
    """Return a process that waits for the first of ``events`` to finish.

    The result of the helper process will be a tuple ``((event, result),
    remaining_events)``. You can pass the list of remaining events to
    another call to this method to wait for the next of them.

    Raise a :exc:`ValueError` if no events are passed.

    """
    if not events:
        raise ValueError('No processes were passed.')

    env = events[0].env

    def waiter():
        for proc in list(events):
            subscribe_at(proc)

        try:
            yield env.suspend()
        except Interrupt as interrupt:
            finished_event, result = interrupt.cause
            events.remove(finished_event)
            env.exit(((finished_event, result), events))

    return env.start(waiter())
