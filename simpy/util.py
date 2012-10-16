"""
This modules contains various utility functions:

- :func:`subscribe_at`: Receive an interrupt if a process terminates.
- :func:`wait_for_all`: Wait until all passed processes have terminated.
- :func:`wait_for_any`: Wait until one of the passed processes has
  terminated.

"""
from simpy.core import Interrupt


def subscribe_at(proc):
    """Register at the process ``proc`` to receive an interrupt when it
    terminates.

    Raise a :exc:`RuntimeError` if ``proc`` has already terminated.

    """
    env = proc._env
    subscriber = env._active_proc

    def _signaller(signaller, receiver):
        yield signaller
        if receiver.is_alive:
            receiver.interrupt(signaller)

    if proc._alive:
        env.start(_signaller(proc, subscriber))
    else:
        raise RuntimeError('%s has already terminated.' % proc)


def wait_for_all(env, procs):
    """Return a process that waits for all ``procs``.

    The result of the helper process will be a list with the results
    of ``procs`` in their respective order.

    Raise a :exc:`ValueError` if no processes are passed.

    """
    if not procs:
        raise ValueError('No processes were passed.')

    def waiter():
        results = []
        for proc in procs:
            results.append((yield proc))

        env.exit(results)

    return env.start(waiter())


def wait_for_any(env, procs):
    """Return a process that waits for the first of ``procs`` to finish.

    The result of the helper process will be a tuple ``(finished_proc,
    remaining_procs)``. You can pass the list of remaining procs to
    another call to this method to wait for the next of them.

    Raise a :exc:`ValueError` if no processes are passed.

    """
    if not procs:
        raise ValueError('No processes were passed.')

    def waiter():
        for proc in procs:
            subscribe_at(proc)

        try:
            yield env.hold()
        except Interrupt as interrupt:
            finished_proc = interrupt.cause
            procs.remove(finished_proc)
            env.exit((finished_proc, procs))

    return env.start(waiter())
