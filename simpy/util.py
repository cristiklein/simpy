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

    :meth:`~simpy.core.Simulation.start` starts a PEM at the current
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

    Raises a :class:`ValueError` if ``delay <= 0``.

    """
    if delay <= 0:
        raise ValueError('delay(=%s) must be > 0.' % delay)

    def starter():
        yield env.timeout(delay)
        proc = env.start(peg)
        env.exit(proc)

    return env.start(starter())


def subscribe_at(proc):
    """Register at the process ``proc`` to receive an interrupt when it
    terminates.

    Raise a :exc:`RuntimeError` if ``proc`` has already terminated.

    """
    env = proc._env
    subscriber = env._active_proc

    def signaller(signaller, receiver):
        result = yield signaller
        if receiver.is_alive:
            receiver.interrupt((signaller, result))

    if proc.is_alive:
        env.start(signaller(proc, subscriber))
    else:
        raise RuntimeError('%s has already terminated.' % proc)


def wait_for_all(procs):
    """Return a process that waits for all ``procs``.

    The result of the helper process will be a list with the results
    of ``procs`` in their respective order.

    Raise a :exc:`ValueError` if no processes are passed.

    """
    if not procs:
        raise ValueError('No processes were passed.')

    env = procs[0]._env

    def waiter():
        # We cannot simply wait for each process because they might
        # terminate in random order which may cause us to wait for an
        # already terminated process.
        for proc in list(procs):
            subscribe_at(proc)

        results = []
        while len(results) < len(procs):
            try:
                yield env.suspend()
            except Interrupt as interrupt:
                finished_proc, result = interrupt.cause
                results.append(result)

        env.exit(results)

    return env.start(waiter())


def wait_for_any(procs):
    """Return a process that waits for the first of ``procs`` to finish.

    The result of the helper process will be a tuple ``(finished_proc,
    remaining_procs)``. You can pass the list of remaining procs to
    another call to this method to wait for the next of them.

    Raise a :exc:`ValueError` if no processes are passed.

    """
    if not procs:
        raise ValueError('No processes were passed.')

    env = procs[0]._env

    def waiter():
        for proc in list(procs):
            subscribe_at(proc)

        try:
            yield env.suspend()
        except Interrupt as interrupt:
            finished_proc, result = interrupt.cause
            procs.remove(finished_proc)
            env.exit(((finished_proc, result), procs))

    return env.start(waiter())
