"""
This modules contains various utility functions:

- :func:`subscribe_at`: Receive an interrupt if a process terminates.
- :func:`wait_for_all`: Wait until all passed processes have terminated.
- :func:`wait_for_any`: Wait until one of the passed processes has
  terminated.

"""
from simpy.core import Interrupt, FAIL


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


def wait_for_all(events, fail_on_error=True, timeout=None):
    """Return a process that waits for all ``events``.

    The result of the helper process will be a list with the results
    of ``events`` in their respective order. The results are either
    the values that can be passed to an event or the return value of a
    :class:`~simpy.core.Process`.

    Raise a :exc:`ValueError` if no events are passed.

    """
    # FIXME This is ugly. It should be allowed to pass in an empty list. This
    # should trigger the wait_for_all event immediately. But there is no
    # environment available without events. Maybe require to pass in env into
    # wait_for_all?
    if not events:
        raise ValueError('No processes were passed.')

    env = events[0].env
    wait_event = env.event()
    pending = {event: idx for idx, event in enumerate(events)}
    results = [None for event in events]

    def waiter(event, evt_type, value):
        idx = pending.pop(event)
        results[idx] = value

        if evt_type is FAIL and fail_on_error:
            # Remove waiter callbacks from remaining pending events.
            for event in pending:
                event.callbacks.remove(waiter)

            wait_event.fail(value)
            return

        if not pending:
            wait_event.succeed(results)

    # Register callbacks.
    # FIXME What should happen if one of the events has already been triggered?
    for event in events:
        event.callbacks.append(waiter)

    if timeout is not None:
        def cancel(event, evt_type, value):
            if wait_event.callbacks is None:
                # Ignore the timeout if all events did already occur.
                return

            # Remove waiter callbacks from remaining pending events.
            for event in pending:
                event.callbacks.remove(waiter)

            wait_event.succeed(results)

        env.timeout(timeout).callbacks.append(cancel)

    return wait_event


def wait_for_any(events, timeout=None):
    """Return a process that waits for the first of ``events`` to finish.

    The result of the helper process will be a tuple ``((event, result),
    remaining_events)``. You can pass the list of remaining events to
    another call to this method to wait for the next of them.

    Raise a :exc:`ValueError` if no events are passed.

    """
    # FIXME See wait_for_all.
    if not events:
        raise ValueError('No processes were passed.')

    env = events[0].env

    wait_event = env.event()
    pending = set(events)
    def waiter(event, evt_type, value):
        if evt_type is not FAIL:
            wait_event.succeed((event, value))
        else:
            # FIXME What should we do in this case? fail only accepts an
            # exception and we can't return the information on which event has
            # failed.
            wait_event.fail(value)

        # Remove waiter callbacks from remaining pending events.
        pending.remove(event)
        for event in pending:
            event.callbacks.remove(waiter)

    # Register callbacks.
    # FIXME What should happen if one of the events has already been triggered?
    for event in events:
        event.callbacks.append(waiter)

    if timeout is not None:
        def cancel(event, evt_type, value):
            if wait_event.callbacks is None:
                # Ignore the timeout if all events did already occur.
                return

            # Remove waiter callbacks from remaining pending events.
            for event in pending:
                event.callbacks.remove(waiter)

            wait_event.succeed(None)

        env.timeout(timeout).callbacks.append(cancel)

    return wait_event
