"""
This module contains the implementation of SimPy's core classes. Not
all of them are intended for direct use and are thus not importable
directly via ``from simpy import ...``.

- :class:`Environment`: SimPy's central class. It contains the
  simulation's state and lets the PEMs interact with it (i.e., schedule
  events).
- :class:`~simpy.core.Process`: This class represents a PEM while
  it is executed in an environment. An instance of it is returned by
  :meth:`Environment.start()`. It inherits :class:`BaseEvent`.
- :class:`Interrupt`: This exception is thrown into a process if it gets
  interrupted by another one.

The following classes should not be imported directly:

- :class:`BaseEvent`: Base class for all events.
- :class:`Timeout`: Can be yielded by a PEM to hold its state or wait
  for a certain amount of time.
- :class:`Event`: A simple event that can be used to implement things
  like shared resources.

This module also contains a few functions to simulate an
:class:`Environment`: :func:`peek()`, :func:`step()` and the shortcut
:func:`simulate()`.

"""
from heapq import heappush, heappop
from inspect import isgenerator
from itertools import count


# BaseEvent types/priorities
EVT_INIT = 0       # First event after a proc was started
EVT_INTERRUPT = 1  # Throw an interrupt into the PEG
EVT_RESUME = 2     # Default event, send value into the PEG

# Constants for successful and failed events
SUCCEED = True
FAIL = False

Infinity = float('inf')


class Interrupt(Exception):
    """This exceptions is sent into a process if it was interrupted by
    another process (see :func:`Process.interrupt()`).

    ``cause`` may be none of no cause was explicitly passed to
    :func:`Process.interrupt()`.

    An interrupt has a higher priority as a normal event. Thus, if
    a process has a normal event and an interrupt scheduled at the same
    time, the interrupt will always be thrown into the PEM first.

    If a process is interrupted multiple times at the same time, all
    interrupts will be thrown into the PEM in the same order as they
    occurred.

    """
    def __init__(self, cause):
        super(Interrupt, self).__init__(cause)

    @property
    def cause(self):
        """Property that returns the cause of an interrupt or ``None``
        if no cause was passed."""
        return self.args[0]


class BaseEvent(object):
    """Base class for all events.

    Every event is bound to an :class:`Environment` ``env`` and has a
    list of ``callbacks`` that are called when the event is processed.

    A callback can be any callable that accepts the following arguments:

    - *event:* The :class:`BaseEvent` instance the callback was
      registered at.
    - *success:* Boolean that indicates if the event was successful.
      A process that raised an uncaught exception might for example
      cause an unsuccessful (failed) event.
    - *value:* An event can optionally send an arbitrary value. It
      defaults to ``None``.

    You can add callbacks by appending them to the ``callbacks``
    attribute of an event.

    """
    __slots__ = ('callbacks', '_env', '_scheduled')

    def __init__(self, env):
        self.callbacks = []
        """List of functions that are called when the event is
        processed."""
        self._env = env
        self._scheduled = False

    @property
    def is_alive(self):
        """``True`` until the event has been processed."""
        return self.callbacks is not None


class Event(BaseEvent):
    """A simple event that can be scheduled by calling its
    :meth:`succeed()` or :meth:`fail()` method.

    You should not instantiate this class directly, but call the factory
    method :meth:`Environment.event()` instead.

    """
    __slots__ = ('callbacks', '_env', '_scheduled')

    def __init__(self, env):
        super(Event, self).__init__(env)

    def succeed(self, value=None):
        """Schedule the event and mark it as successful.

        You can optionally pass an arbitrary ``value`` that will be sent
        into processes waiting for that event.

        Raise a :exc:`RuntimeError` if this event has already been
        scheduled.

        """
        self._env._schedule(EVT_RESUME, self, SUCCEED, value)

    def fail(self, exception):
        """Schedule the event and mark it as failed.

        The ``exception`` will be thrown into processes waiting for that
        event.

        Raise a :exc:`ValueError` if ``exception`` is not an
        :exc:`Exception`.

        Raise a :exc:`RuntimeError` if this event has already been
        scheduled.

        """
        if not isinstance(exception, Exception):
            raise ValueError('%s is not an exception.' % exception)
        self._env._schedule(EVT_RESUME, self, FAIL, exception)


class Timeout(BaseEvent):
    """An event that is scheduled with a certain ``delay`` after its
    creation.

    This event can be used by processes to wait (or hold their state)
    for ``delay`` time steps. It is immediately scheduled at ``env.now
    + delay`` and has thus (in contrast to :class:`Event`) no
    *success()* or *fail()* method.

    """
    __slots__ = ('callbacks', '_env', '_scheduled')

    def __init__(self, env, delay, value=None):
        if delay < 0:
            raise ValueError('Negative delay %s' % delay)
        super(Timeout, self).__init__(env)
        env._schedule(EVT_RESUME, self, SUCCEED, value, delay)


class Process(BaseEvent):
    """A *Process* is a wrapper for instantiated PEMs during their
    execution.

    A Processes has a generator (the generator that the PEM returns) and
    a reference to its :class:`Environment` ``env``. It also contains
    internal and external status information.  It is also used for
    process interaction, e.g., for interruptions.

    ``Process`` inherits :class:`BaseEvent`. You can thus wait for the
    termination of a process by simply yielding it from your PEM.

    An instance of this class is returned by
    :meth:`Environment.start()`.

    """
    __slots__ = ('callbacks', '_env', '_scheduled',
                 'name', '_generator', '_target')

    def __init__(self, env, generator):
        if not isgenerator(generator):
            raise ValueError('%s is not a generator.' % generator)

        super(Process, self).__init__(env)

        self.name = generator.__name__
        """The process name."""

        self._generator = generator
        self._target = None

        init_event = BaseEvent(env)
        init_event.callbacks.append(self._process)
        env._schedule(EVT_INIT, init_event, SUCCEED)

    def __repr__(self):
        """Return a string "Process(pem_name)"."""
        return '%s(%s)' % (self.__class__.__name__, self.name)

    def interrupt(self, cause=None):
        """Interupt this process optionally providing a ``cause``.

        A process cannot be interrupted if it already terminated.
        A process can also not interrupt itself. Raise
        a :exc:`RuntimeError` in these cases.

        """
        if not self.is_alive:
            raise RuntimeError('%s has terminated and cannot be interrupted.' %
                               self)

        if self is self._env.active_process:
            raise RuntimeError('A process is not allowed to interrupt itself.')

        # Unsubscribe the event we were waiting for
        if self._target:
            self._target.callbacks.remove(self._process)
            self._target = None

        # Schedule interrupt event
        event = BaseEvent(self._env)
        event.callbacks.append(self._process)
        self._env._schedule(EVT_INTERRUPT, event, FAIL, Interrupt(cause))

    def _process(self, event, success, value):
        """Get the next event from this process and register as a callback.

        If the PEM generator exits or raises an exception, terminate
        this process. Also schedule this process to notify all
        registered callbacks, that the process terminated.

        """
        # Ignore dead processes. Multiple concurrently scheduled
        # interrupts cause this situation. If the process dies while
        # handling the first one, the remaining interrupts must be
        # discarded.
        if not self.is_alive:
            return

        # Mark the current process as active.
        self._env._active_proc = self
        self._target = None

        # Get next event from process
        try:
            new_event = self._generator.send(value) if success else \
                        self._generator.throw(value)

        # We should have been interrupted but already terminated.
        except Interrupt as interrupt:
            # NOTE: It would be nice if we could throw an error into the
            # processes that caused the illegal interrupt, but this
            # error can only be detected once the second interrupt is
            # thrown into the terminated victim.
            raise RuntimeError('Illegal Interrupt(%s) for %s.' %
                               (interrupt.cause, self))

        # The generator exited or raised an exception.
        except (StopIteration, BaseException) as err:
            if type(err) is StopIteration:
                success = SUCCEED
                value = err.args[0] if len(err.args) else None

            else:
                if not self.callbacks:
                    raise err
                success = FAIL
                # FIXME Isn't there a better way to obtain the exception
                # type? For example using (type, value, traceback)
                # tuple?
                value = type(err)(*err.args)
                value.__cause__ = err

            self._env._schedule(EVT_RESUME, self, success, value)
            self._env._active_proc = None
            return

        # Check yielded event
        try:
            if new_event.is_alive:
                new_event.callbacks.append(self._process)
                self._target = new_event
            else:
                # FIXME This is dangerous. If the process catches these
                # exceptions it may yield another event, which will not get
                # processed causing the process to become deadlocked.
                self._generator.throw(
                        ValueError('%s already terminated.' % new_event))
        except AttributeError:
            # FIXME Same problem as above.
            self._generator.throw(
                    ValueError('Invalid yield value "%s"' % new_event))

        self._env._active_proc = None


class Environment(object):
    """The *environment* contains the simulation state and provides a
    basic API for processes to interact with it.

    """
    def __init__(self, initial_time=0):
        self._now = initial_time
        self._events = []
        self._eid = count()
        self._active_proc = None

    @property
    def active_process(self):
        """Property that returns the currently active process."""
        return self._active_proc

    @property
    def now(self):
        """Property that returns the current simulation time."""
        return self._now

    def start(self, generator):
        """Start and return a new :class:`Process` for ``generator``.

        ``generator`` is the generator returned by a *PEM*.

        """
        return Process(self, generator)

    def exit(self, result=None):
        """Stop the current process, optionally providing a ``result``.

        The ``result`` is sent to processes waiting for the current
        process.

        """
        raise StopIteration(result)

    def event(self):
        """Create and return a new :class:`Event`."""
        return Event(self)

    def timeout(self, delay, value=None):
        """Schedule (and return) a new :class:`Timeout` event for
        ``delay`` time units.

        Raise a :exc:`ValueError` if ``delta_t < 0``.

        You can optionally pass a ``value`` which will be sent back to
        the PEM when it continues. This might be helpful to e.g.
        implement resources (:class:`simpy.resources.Store` uses this
        feature).

        """
        return Timeout(self, delay, value)

    def suspend(self):
        """Return a :class:`BaseEvent`.

        That event can and will not be scheduled. Yielding that event
        will suspend the processes until it is interrupted by another
        one.

        """
        return BaseEvent(self)

    def _schedule(self, evt_type, event, succeed, value=None, delay=None):
        """Schedule the given ``event`` of type ``evt_type``.

        ``evt_type`` should be one of the ``EVT_*`` constants defined on
        top of this module.

        If ``succeed`` is ``True``, the optional ``value`` will be sent
        into all processes waiting for that event.

        If ``succeed`` is ``False``, the exception in ``value`` is
        thrown into all processes waiting for that event.

        The event will be scheduled at the simulation time ``self._now
        + delay`` or at the current time if no value is provided.

        Raise a :exc:`RuntimeError` if the event already has an event
        scheduled.

        """
        if event._scheduled:
            raise RuntimeError('BaseEvent %s already scheduled.' % event)

        if delay is None:
            delay = 0

        heappush(self._events, (
            (self._now + delay),
            evt_type,
            next(self._eid),
            succeed,
            event,
            value,
        ))
        event._scheduled = True


def peek(env):
    """Return the time of the Environment ``env``'s next event or
    ``inf`` if the event queue is empty.

    """
    try:
        return env._events[0][0]  # time of first event
    except IndexError:
        return Infinity


def step(env):
    """Get and process the next event for the Environment ``env``.

    Raise an :exc:`IndexError` if no valid event is on the heap.

    """
    env._now, evt_type, eid, succeed, event, value = heappop(env._events)

    # Mark event as processed.
    callbacks, event.callbacks = event.callbacks, None

    for callback in callbacks:
        callback(event, succeed, value)


def simulate(env, until=Infinity):
    """Shortcut for ``while peek(env) < until: step(env)``.

    The parameter ``until`` specifies when the simulation ends. By
    default it is set to *infinity*, which means SimPy tries to simulate
    all events, which might take infinite time if your processes don't
    terminate on their own.

    """
    if until <= 0:
        raise ValueError('until(=%s) should be a number > 0.' % until)

    while peek(env) < until:
        step(env)
