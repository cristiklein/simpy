"""
This modules contains various utility functions:

- :func:`wait_for_all`: Wait until all passed processes have terminated.
- :func:`wait_for_any`: Wait until one of the passed processes has
  terminated.

"""
from simpy.core import Interrupt


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
