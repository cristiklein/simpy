"""
This modules contains various utility functions:

- :func:`at`: Start a process at a certain time in the future.
- :func:`delayed`: Start a process after a certain time has passed.
- :func:`wait_for_all`: Wait until all passed processes have terminated.
- :func:`wait_for_any`: Wait until one of the passed processes has
  terminated.

"""
from simpy.core import Interrupt


def at(t):
    """Return a helper PEM to start another PEM at time ``t``.

    :meth:`~simpy.Simulation.start` starts a PEM at the current
    simulation time. This helper allows you to start a PEM at a defined
    point in the future.

    Just pass it as a first parameter to ``start()``::

        >>> def pem(context, x):
        >>>     print('%s, %s' % (context.now, x))
        >>>     yield context.hold(1)

        >>> sim = Simulation()
        >>> sim.start(at(5), pem, x=3)
        >>> sim.simulate()
        5, 3

    The helper process returned by this method raises
    a :class:`ValueError` if ``t`` is not in the future.

    """
    def starter(context, target, *args, **kwargs):
        if t <= context.now:
            raise ValueError('t(=%s) must be in the future (>%s)' %
                    (t, context.now))

        yield context.hold(t - context.now)
        context.start(target, *args, **kwargs)

    return starter


def delayed(dt):
    """Return a helper PEM to start another PEM after a delay of ``dt``.

    :meth:`~simpy.Simulation.start` starts a PEM at the current
    simulation time. This helper allows you to start a PEM after a delay
    of ``dt`` simulation time units.

    Just pass it as a first parameter to ``start()``::

        >>> def pem(context, x):
        >>>     print('%s, %s' % (context.now, x))
        >>>     yield context.hold(1)

        >>> sim = Simulation()
        >>> sim.start(delayed(5), pem, x=3)
        >>> sim.simulate()
        5, 3

    Raises a :class:`ValueError` if ``dt <= 0``.

    """
    if dt <= 0:
        raise ValueError('dt(=%s) must be > 0.' % dt)

    def starter(context, target, *args, **kwargs):
        yield context.hold(dt)
        context.start(target, *args, **kwargs)

    return starter


def wait_for_all(procs):
    """Return a process that waits for all ``procs``.

    The result of the helper process will be a list with the results
    of ``procs`` in their respective order.

    Raise a :class:`ValueError` if no processes are passed.

    """
    if not procs:
        raise ValueError('No processes were passed.')

    def waiter(context):
        results = []
        for proc in procs:
            results.append((yield proc))

        context.exit(results)

    return waiter


def wait_for_any(procs):
    """Return a process that waits for the first of ``procs`` to finish.

    The result of the helper process will be a tuple ``(finished_proc,
    remaining_procs)``. You can pass the list of remaining procs to
    another call to this method to wait for the next of them.

    Raise a :class:`ValueError` if no processes are passed.

    """
    if not procs:
        raise ValueError('No processes were passed.')

    def waiter(context):
        for proc in procs:
            context.interrupt_on(proc)

        try:
            yield context.hold()
        except Interrupt as interrupt:
            finished_proc = interrupt.cause
            procs.remove(finished_proc)
            context.exit((finished_proc, procs))

    return waiter
