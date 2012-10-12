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


# Event types
EVT_INTERRUPT = 0  # Throw an error into the PEG
EVT_RESUME = 1  # Default event, send value into the PEG
EVT_INIT = 2  # First event after a proc was started
EVT_SUSPEND = 3  # Suspend the process

# Process states
STATE_FAILED = 0
STATE_SUCCEEDED = 1

Infinity = float('inf')


Event = object()
"""Yielded by a PEM if it waits for an event (e.g. via "yield ctx.hold(1))."""


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


class Process(object):
    """A *Process* is a wrapper for instantiated PEMs.

    A Processes has a process event generator (``peg`` -- the generator
    that the PEM returns) and a reference to its :class:`Environment`
    ``env``. It also contains internal and external status information.
    It is also used for process interaction, e.g., for interruptions.

    An instance of this class is returned by
    :meth:`Environment.start()`.

    """
    __slots__ = ('name', 'result', '_peg', '_env', '_alive',
                 '_next_event', '_joiners', '_observers', '_interrupts')

    def __init__(self, peg, env):
        self.name = peg.__name__
        """The process name."""

        self.result = None
        """The process' result after it terminated."""

        self._peg = peg
        self._env = env
        self._alive = True
        self._next_event = None

        self._joiners = []  # Procs that wait for this one
        self._observers = []  # Procs that want to get interrupted
        self._interrupts = []  # Pending interrupts for this proc

    @property
    def is_alive(self):
        """``False`` if the PEG stopped."""
        return self._alive

    def __repr__(self):
        """Return a string "Process(pem_name)"."""
        return '%s(%s)' % (self.__class__.__name__, self.name)

    def interrupt(self, cause=None):
        """Interupt this process optionally providing a ``cause``.

        A process cannot be interrupted if it is suspended (and has no
        event scheduled) or if it was just initialized and could not
        issue a *hold* yet. Raise a :exc:`RuntimeError` in both cases.

        """
        if not self._next_event:
            raise RuntimeError('%s has no event scheduled and cannot be '
                            'interrupted.' % self)
        if self._next_event[0] is EVT_INIT:
            raise RuntimeError('%s was just initialized and cannot yet be '
                            'interrupted.' % self)
        if self._next_event[0] is EVT_SUSPEND:
            raise RuntimeError('%s is suspended and cannot be interrupted.' %
                                self)

        interrupts = self._interrupts
        interrupt = Interrupt(cause)

        # If it is the first interrupt, schedule it. Else, just append it.
        if self._next_event[0] is not EVT_INTERRUPT:
            self._next_event = None
            _schedule(self._env, self, EVT_INTERRUPT, interrupt)
        else:
            interrupts.append(interrupt)

    def resume(self, value=None):
        """Resume this process.

        You can optionally pass a ``value`` which will be sent to the
        resumed PEM when it continues. This might be helpful to e.g.
        implement resources (:class:`simpy.resources.Store` uses this
        feature).

        Raise a :exc:`RuntimeError` if the process is not suspended.

        """
        if self._next_event[0] is not EVT_SUSPEND:
            raise RuntimeError('%s is not suspended.' % self)

        self._next_event = None
        _schedule(self._env, self, EVT_RESUME, value=value)

    def subscribe(self):
        """Register at the process to receive an interrupt when it terminates.
        """
        proc = self._env._active_proc

        if self._alive:
            self._observers.append(proc)
        else:
            proc._interrupts.append(Interrupt(self))


class Environment(object):
    """The *environment* contains the simulation state and provides a
    basic API for processes to interact with it.

    """
    def __init__(self):
        self._events = []

        self._eid = count()
        self._active_proc = None
        self._now = 0

    @property
    def active_process(self):
        """Property that returns the currently active process."""
        return self._active_proc

    @property
    def now(self):
        """Property that returns the current simulation time."""
        return self._now

    def start(self, peg, at=None, delay=None):
        """Start a new process for ``peg``.

        *PEG* is the *Process Execution Generator*, which is the
        generator returned by *PEM*.

        The process is started at the current simulation time, but you
        can alternatively specify a start time via ``at`` or a delayed
        start via ``delay``. ``delay`` takes precedence over ``at`` if
        both are specified.

        Raise a :exc:`ValueError` if ``peg`` is not a generator, if
        ``at`` is smaller than the current simulation time or if
        ``delay`` is negative.

        """
        if not isgenerator(peg):
            raise ValueError('PEG %s is not a generator.' % peg)

        if at and at < self._now:
            raise ValueError('at(=%s) must be > %s' % (at, self._now))

        if delay:
            if delay < 0:
                raise ValueError('delay(=%s) must be > 0' % delay)

            at = self._now + delay

        proc = Process(peg, self)
        _schedule(self, proc, EVT_INIT, at=at)

        return proc

    def exit(self, result=None):
        """Stop the current process, optionally providing a ``result``.

        The ``result`` is sent to processes waiting for the current
        process and can also be obtained via :attr:`Process.result`.

        """
        self._active_proc.result = result
        raise StopIteration()

    def hold(self, delta_t=Infinity, value=None):
        """Schedule a new event in ``delta_t`` time units.

        If ``delta_t`` is omitted, schedule an event at *infinity*. This
        is a week suspend. A process holding until *infinity* can only
        become active again if it gets interrupted.

        Raise a :exc:`ValueError` if ``delta_t < 0``.

        You can optionally pass a ``value`` which will be sent back to
        the PEM when it continues. This might be helpful to e.g.
        implement resources (:class:`simpy.resources.Store` uses this
        feature).

        The result of that method must be ``yield``\ ed. Raise
        a :exc:`RuntimeError` if this (or another event-generating)
        method was previously called without yielding its result.

        """
        if delta_t < 0:
            raise ValueError('delta_t=%s must be >= 0.' % delta_t)

        _schedule(self, self._active_proc, EVT_RESUME, value=value,
                    at=(self._now + delta_t))

        return Event

    def suspend(self):
        """Suspend the current process by deleting all future events.

        A suspended process needs to be resumed (see
        :meth:`Process.resume()`) by another process to get active
        again.

        As with :meth:`~Environment.hold()`, the result of that method
        must be ``yield``\ ed. Raise a :exc:`RuntimeError` if the
        process has already an event scheduled.

        """
        _schedule(self, self._active_proc, EVT_SUSPEND)

        return Event


def peek(env):
    """Return the time of the Environment ``env``'s next event or
    ``inf`` if the event queue is empty.

    """
    try:
        while True:
            # Pop all removed events from the queue
            # env._events[0][3] is the scheduled event
            # env._events[0][2] is the corresponding proc
            if env._events[0][3] is env._events[0][2]._next_event:
                break
            heappop(env._events)

        return env._events[0][0]  # time of first event

    except IndexError:
        return Infinity


def step(env):
    """Get and process the next event for the Environment ``env``.

    Raise an :exc:`IndexError` if no valid event is on the heap.

    """
    if env._active_proc:
        raise RuntimeError('step() was called from within step().'
                            'Something went horribly wrong.')

    # Get the next valid event from the heap
    while True:
        env._now, eid, proc, evt = heappop(env._events)

        # Break from the loop if we find a valid event.
        if evt is proc._next_event:
            break

    env._active_proc = proc

    evt_type, value = evt
    proc._next_event = None
    interrupts = proc._interrupts

    # Get next event from process
    try:
        if evt_type is EVT_INTERRUPT:
            target = proc._peg.throw(value)
        else:
            target = proc._peg.send(value)

    # env._active_proc has terminated
    except StopIteration:
        _join(env, proc)
        env._active_proc = None

        return  # Don't need to check a new event

    # Check what was yielded
    if type(target) is Process:
        if proc._next_event:
            proc._peg.throw(RuntimeError('%s already has an event '
                    'scheduled. Did you forget to yield?' % proc))

        if target.is_alive:
            # Schedule a hold(Infinity) so that the waiting proc can
            # be interrupted if target terminates.
            proc._next_event = (EVT_RESUME, None)
            target._joiners.append(proc)

        else:
            # Process has already terminated. Resume as soon as possible.
            _schedule(env, proc, EVT_RESUME, target.result)

    elif target is not Event:
        proc._peg.throw(ValueError('Invalid yield value: %s' % target))

    # else: target is event

    # Schedule concurrent interrupts.
    if interrupts:
        proc._next_event = None
        _schedule(env, proc, EVT_INTERRUPT, interrupts.pop(0))

    env._active_proc = None


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


def _schedule(env, proc, evt_type, value=None, at=None):
    """Schedule a new event for process ``proc``.

    ``evt_type`` should be one of the ``EVT_*`` constants defined on
    top of this module.

    The optional ``value`` will be sent into the PEG when the event is
    processed.

    The event will be scheduled at the simulation time ``at`` or at the
    current time if no value is provided.

    Raise a :exc:`RuntimeError` if ``proc`` already has an event
    scheduled.

    """
    if proc._next_event:
        raise RuntimeError('%s already has an event scheduled. Did you '
                        'forget to yield?' % proc)

    proc._next_event = (evt_type, value)

    # Don't put anything on the heap for a suspended proc.
    if evt_type is EVT_SUSPEND:
        return

    # Don't put events scheduled for "Infinity" onto the heap,
    # because the will never be popped.
    if at is Infinity:
        return

    if at is None:
        at = env._now

    heappush(env._events, (at, next(env._eid), proc, proc._next_event))


def _join(env, proc):
    """Notify all registered processes that the process ``proc`` terminated."""
    joiners = proc._joiners
    observers = proc._observers

    proc._alive = False

    for joiner in joiners:
        # A joiner is always alive, since "yield proc" blocks until
        # "proc" has terminated.
        joiner._next_event = None
        _schedule(env, joiner, EVT_RESUME, proc.result)

    for observer in observers:
        if not observer.is_alive:
            continue
        observer.interrupt(proc)
