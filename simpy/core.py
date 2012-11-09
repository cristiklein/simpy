"""
This module contains the implementation of SimPy's core classes. Not
all of them are intended for direct use and are thus not importable
directly via ``from simpy import ...``.

* :class:`Environment`: SimPy's central class. It contains the
  simulation's state and lets the PEMs interact with it (i.e., schedule
  events).

* :class:`Interrupt`: This exception is thrown into a process if it gets
  interrupted by another one.

The following classes should not be imported directly:

* :class:`~simpy.core.Process`: An instance of that class is returned by
  :meth:`Environment.start()`.

This module also contains a few functions to simulate an
:class:`Environment`.

"""
from heapq import heappush, heappop
from inspect import isgenerator
from itertools import count


# Event types/priorities
(
    EVT_INIT,       # First event after a proc was started
    EVT_INTERRUPT,  # Throw an interrupt into the PEG
    EVT_RESUME,     # Default event, send value into the PEG
) = range(3)

# Constants for successful and failed events
SUCCEED = True
FAIL = False

Infinity = float('inf')


class Interrupt(Exception):
    """This exceptions is sent into a process if it was interrupted by
    another process (see :func:`Process.interrupt()`).

    ``cause`` may be none of no cause was explicitly passed to
    :func:`Process.interrupt()`.

    """
    def __init__(self, cause):
        super(Interrupt, self).__init__(cause)

    @property
    def cause(self):
        """Property that returns the cause of an interrupt or ``None``
        if no cause was passed."""
        return self.args[0]


class Event(object):
    __slots__ = ('callbacks', '_env', '_scheduled')

    def __init__(self, env):
        self.callbacks = []
        self._env = env
        self._scheduled = False

    @property
    def is_alive(self):
        """``False`` if the PEG stopped."""
        return self.callbacks is not None


class Timeout(Event):
    __slots__ = ('callbacks', '_env', '_scheduled')

    def __init__(self, env, delay, value=None):
        if delay < 0:
            raise ValueError('Negative delay %s' % delay)
        super(Timeout, self).__init__(env)
        env._schedule(EVT_RESUME, self, SUCCEED, value, delay)


class Process(Event):
    """A *Process* is a wrapper for instantiated PEMs.

    A Processes has a process event generator (``peg`` -- the generator
    that the PEM returns) and a reference to its :class:`Environment`
    ``env``. It also contains internal and external status information.
    It is also used for process interaction, e.g., for interruptions.

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

        init_event = Event(env)
        init_event.callbacks.append(self._process)
        env._schedule(EVT_INIT, init_event, SUCCEED)

    def __repr__(self):
        """Return a string "Process(pem_name)"."""
        return '%s(%s)' % (self.__class__.__name__, self.name)

    def interrupt(self, cause=None):
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
        event = Event(self._env)
        event.callbacks.append(self._process)
        self._env._schedule(EVT_INTERRUPT, event, FAIL, Interrupt(cause))

    def _process(self, event, succeed, value):
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
            new_event = self._generator.send(value) if succeed else \
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
                succeed = SUCCEED
                value = err.args[0] if len(err.args) else None

            else:
                if not self.callbacks:
                    raise err
                succeed = FAIL
                # FIXME Isn't there a better way to obtain the exception
                # type? For example using (type, value, traceback)
                # tuple?
                value = type(err)(*err.args)
                value.__cause__ = err

            self._env._schedule(EVT_RESUME, self, succeed, value)
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
        """Start a new process for ``generator``.

        ``generator`` is the generator returned by a *PEM*.

        """
        return Process(self, generator)

    def exit(self, result=None):
        """Stop the current process, optionally providing a ``result``.

        The ``result`` is sent to processes waiting for the current
        process and can also be obtained via :attr:`Process.result`.

        """
        raise StopIteration(result)

    def timeout(self, delay, value=None):
        """Schedule a new event in ``delay`` time units.

        Raise a :exc:`ValueError` if ``delta_t < 0``.

        You can optionally pass a ``value`` which will be sent back to
        the PEM when it continues. This might be helpful to e.g.
        implement resources (:class:`simpy.resources.Store` uses this
        feature).

        """
        return Timeout(self, delay, value)

    def suspend(self):
        return Event(self)

    def _schedule(self, evt_type, event, succeed, value=None, delay=None):
        if event._scheduled:
            raise RuntimeError('Event %s already scheduled.' % event)

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
