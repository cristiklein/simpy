"""
This module contains the implementation of SimPy's core classes. Not
all of them are intended for direct use and are thus not importable
directly via ``from simpy import ...``.

* :class:`~simpy.core.Simulation`: SimPy's central class that starts
  the processes and performs the simulation.

* :class:`~simpy.core.Interrupt`: This exception is thrown into
  a process if it gets interrupted by another one.

The following classes should not be imported directly:

* :class:`~simpy.core.Context`: An instance of that class is created by
  :class:`~simpy.core.Simulation` and passed to every PEM that is
  started.

* :class:`~simpy.core.Process`: An instance of that class is returned by
  :meth:`simpy.core.Simulation.start` and
  :meth:`simpy.core.Context.start`.

"""
from heapq import heappush, heappop
from inspect import isgeneratorfunction
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
    another process (see :func:`Context.interrupt()`).

    ``cause`` may be none of no cause was explicitly passed to
    :func:`Context.interrupt()`.

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

    A Processes has a unique process ID (``pid``) and a process event
    generator (``peg`` -- the generator that the PEM returns). It also
    contains internal and external status information. It is also used
    for process interaction, e.g., for interruptions.

    An instance of this class is returned by :func:`Context.start()`
    and :func:`Simulation.start()`.

    """
    __slots__ = ('pid', 'name', 'result', '_peg', '_alive',
                 '_next_event', '_joiners', '_observers', '_interrupts')

    def __init__(self, pid, peg):
        self.pid = pid
        """The process ID."""

        self.name = peg.__name__
        """The process name."""

        self.result = None
        """The process' result after it terminated."""

        self._peg = peg
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
        """Return a string "Process(pid, pem_name)"."""
        return '%s(%s, %s)' % (self.__class__.__name__, self.pid, self.name)


def start(sim, pem, *args, **kwargs):
    """Start a new process for ``pem``.

    Pass the simulation :class:`Context` and, optionally, ``*args`` and
    ``**kwargs`` to the PEM.

    Raise a :exc:`ValueError` if ``pem`` is not a generator function.

    """
    if not isgeneratorfunction(pem):
        raise ValueError('PEM %s is not a generator function.' % pem)

    peg = pem(sim.context, *args, **kwargs)

    proc = Process(next(sim._pid), peg)
    sim._schedule(proc, EVT_INIT)

    return proc


def exit(sim, result=None):
    """Stop the current process, optinally providing a ``result``.

    The ``result`` is sent to processes waiting for the current process
    and can also be obtained via :attr:`Process.result`.

    """
    sim._active_proc.result = result
    raise StopIteration()


def hold(sim, delta_t=Infinity, value=None):
    """Schedule a new event in ``delta_t`` time units.

    If ``delta_t`` is omitted, schedule an event at *infinity*. This is
    a week suspend. A process holding until *infinity* can only become
    active again if it gets interrupted.

    Raise a :exc:`ValueError` if ``delta_t < 0``.

    You can optionally pass a ``value`` which will be sent back to the
    PEM when it continues. This might be helpful to e.g. implement
    resources (:class:`simpy.resources.Store` uses this feature).

    The result of that method must be ``yield``\ ed. Raise
    a :exc:`RuntimeError` if this (or another event-generating) method
    was previously called without yielding its result.

    """
    if delta_t < 0:
        raise ValueError('delta_t=%s must be >= 0.' % delta_t)

    sim._schedule(sim._active_proc, EVT_RESUME, value=value,
                  at=(sim._now + delta_t))

    return Event


def interrupt(sim, other, cause=None):
    """Interupt ``other`` process optionally providing a ``cause``.

    Another process cannot be interrupted if it is suspend (and has no
    event scheduled) or if it was just initialized and could not issue
    a *hold* yet. Raise a :exc:`RuntimeError` in both cases.

    """
    if not other._next_event:
        raise RuntimeError('%s has no event scheduled and cannot be '
                           'interrupted.' % other)
    if other._next_event[0] is EVT_INIT:
        raise RuntimeError('%s was just initialized and cannot yet be '
                           'interrupted.' % other)
    if other._next_event[0] is EVT_SUSPEND:
        raise RuntimeError('%s is suspended and cannot be interrupted.' %
                            other)

    interrupts = other._interrupts
    interrupt = Interrupt(cause)

    # If it is the first interrupt, schedule it. Else, just append it.
    if other._next_event[0] is not EVT_INTERRUPT:
        other._next_event = None
        sim._schedule(other, EVT_INTERRUPT, interrupt)
    else:
        interrupts.append(interrupt)


def suspend(sim):
    """Suspend the current process by deleting all future events.

    A suspended process needs to be resumed (see
    :class:`Context.resume()`) by another process to get active again.

    As with :func:`~Context.hold()`, the result of that method must be
    ``yield``\ ed. Raise a :exc:`RuntimeError` if the process has
    already an event scheduled.

    """
    sim._schedule(sim._active_proc, EVT_SUSPEND)

    return Event


def resume(sim, other, value=None):
    """Resume the suspended process ``other``.

    You can optionally pass a ``value`` which will be sent to the
    resumed PEM when it continues. This might be helpful to e.g.
    implement resources (:class:`simpy.resources.Store` uses this
    feature).

    Raise a :exc:`RuntimeError` if ``other`` is not suspended.

    """
    if other._next_event[0] is not EVT_SUSPEND:
        raise RuntimeError('%s is not suspended.' % other)

    other._next_event = None
    sim._schedule(other, EVT_RESUME, value=value)


def interrupt_on(sim, other):
    """Register at ``other`` to receive an interrupt when it terminates."""
    proc = sim._active_proc

    if other.is_alive:
        other._observers.append(proc)
    else:
        proc._interrupts.append(Interrupt(other))


class Context(object):
    """This class provides the API for process to interact with the
    simulation and other processes.

    Every instance of :class:`Simulation` has exactly one context
    associated with it. It is passed to every PEM when it is called.

    """
    # All methods (like hold or interrupt) are added to the context
    # instance by the Simulation and they are all bound to the
    # Simulation instance.

    def __init__(self, sim):
        self._sim = sim

    @property
    def active_process(self):
        """Property that returns the currently active process."""
        return self._sim._active_proc

    @property
    def now(self):
        """Property that returns the current simulation time."""
        return self._sim._now


class Simulation(object):
    """This is SimPy's central class and actually performs a simulation.

    It manages the processes' events and coordinates their execution.

    Processes interact with the simulation via a simulation
    :class:`Context` object that is passed to every process when it is
    started.

    """
    """"""
    # The following functions are all bound to a Simulation instance and
    # are later set as attributes to the Context and Simulation
    # instances.
    # Since some of these methods are shared between the Simulation and
    # Context and some are exclusively for the Context, they are defined
    # as module level Functions to keep the Simulation and Context APIs
    # clean.
    context_funcs = (start, exit, hold, interrupt, suspend, resume,
                     interrupt_on)
    simulation_funcs = (start,)

    def __init__(self):
        self._events = []

        self._pid = count()
        self._eid = count()
        self._active_proc = None
        self._now = 0

        self.context = Context(self)

        # Attach context function and bind them to the simulation.
        for func in self.context_funcs:
            setattr(self.context, func.__name__,
                    func.__get__(self, Simulation))

        # Attach public simulation functions to this instance.
        for func in self.simulation_funcs:
            setattr(self, func.__name__, func.__get__(self, Simulation))

    @property
    def now(self):
        """Property that returns the current simulation time."""
        return self._now

    def peek(self):
        """Return the time of the next event or ``inf`` if the event
        queue is empty.

        """
        try:
            while True:
                # Pop all removed events from the queue
                # self._events[0][3] is the scheduled event
                # self._events[0][2] is the corresponding proc
                if self._events[0][3] is self._events[0][2]._next_event:
                    break
                heappop(self._events)

            return self._events[0][0]  # time of first event

        except IndexError:
            return Infinity

    def step(self):
        """Get and process the next event.

        Raise an :exc:`IndexError` if no valid event is on the heap.

        """
        if self._active_proc:
            raise RuntimeError('step() was called from within step().'
                               'Something went horribly wrong.')

        # Get the next valid event from the heap
        while True:
            self._now, eid, proc, evt = heappop(self._events)

            # Break from the loop if we find a valid event.
            if evt is proc._next_event:
                break

        self._active_proc = proc

        evt_type, value = evt
        proc._next_event = None
        interrupts = proc._interrupts

        # Get next event from process
        try:
            if evt_type is EVT_INTERRUPT:
                target = proc._peg.throw(value)
            else:
                target = proc._peg.send(value)

        # self._active_proc has terminated
        except StopIteration:
            self._join(proc)
            self._active_proc = None

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
                self._schedule(proc, EVT_RESUME, target.result)

        elif target is not Event:
            proc._peg.throw(ValueError('Invalid yield value: %s' % target))

        # else: target is event

        # Schedule concurrent interrupts.
        if interrupts:
            proc._next_event = None
            self._schedule(proc, EVT_INTERRUPT, interrupts.pop(0))

        self._active_proc = None

    def simulate(self, until=Infinity):
        """Shortcut for ``while sim.peek() < until: sim.step()``.

        The parameter ``until`` specifies when the simulation ends.
        By default it is set to *infinity*, which means SimPy tries to
        simulate all events, which might take infinite time if your
        processes don't terminate on their own.

        """
        if until <= 0:
            raise ValueError('until(=%s) should be a number > 0.' % until)

        while self.peek() < until:
            self.step()

    def _schedule(self, proc, evt_type, value=None, at=None):
        """Schedule a new event for process ``proc``.

        ``evt_type`` should be one of the ``EVT_*`` constants defined on
        top of this module.

        The optional ``value`` will be sent into the PEG when the event
        is processed.

        The event will be scheduled at the simulation time ``at`` or at
        the current time if no value is provided.

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
            at = self._now

        heappush(self._events, (at, next(self._eid), proc, proc._next_event))

    def _join(self, proc):
        """Notify all registered processes that the process ``proc``
        terminated.

        """
        joiners = proc._joiners
        observers = proc._observers

        proc._alive = False

        for joiner in joiners:
            # A joiner is always alive, since "yield proc" blocks until
            # "proc" has terminated.
            joiner._next_event = None
            self._schedule(joiner, EVT_RESUME, proc.result)

        for observer in observers:
            if not observer.is_alive:
                continue
            self.context.interrupt(observer, proc)
