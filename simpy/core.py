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
    another process.

    """
    def __init__(self, cause):
        super(Interrupt, self).__init__(cause)

    @property
    def cause(self):
        return self.args[0]


class Process(object):
    """A *Process* is a wrapper for instantiated PEMs.

    A Processes needs a unique process ID (*pid*) and a process event
    generator (*peg* -- the generator that the PEM returns).

    The *Process* class contains internal and external status
    information. It is also used for process interaction, e.g., for
    interruptions.

    """
    __slots__ = ('pid', 'name', 'result', 'is_alive', '_peg', '_alive',
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

    Pass *simulation context* and, optionally, ``*args`` and
    ``**kwargs`` to the PEM.

    If ``pem`` is not a generator function, raise a :class`ValueError`.

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


def hold(sim, delta_t=Infinity):
    """Schedule a new event in ``delta_t`` time units.

    If ``delta_t`` is omitted, schedule an event at *infinity*. This is
    a week suspend. A process holding until *infinity* can only become
    active again if it gets interrupted.

    Raise a :class:`ValueError` if ``delta_t < 0``.

    Raise a :class:`RuntimeError` if this (or another event-generating)
    method was previously called without yielding its result.

    """
    if delta_t < 0:
        raise ValueError('delta_t=%s must be >= 0.' % delta_t)

    sim._schedule(sim._active_proc, EVT_RESUME, at=(sim._now + delta_t))

    return Event


def interrupt(sim, other, cause=None):
    """Interupt ``other`` process optionally providing a ``cause``.

    Another process cannot be interrupted if it is suspend (and has no
    event scheduled) or if it was just initialized and could not issue
    a *hold* yet. Raise a :class:`RuntimeError` in both cases.

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
    :class:`Context.resume`) by another process to get active again.

    Raise a :class:`RuntimeError` if the process has already an event
    scheduled.

    """
    sim._schedule(sim._active_proc, EVT_SUSPEND)

    return Event


def resume(sim, other):
    """Resume the suspended process ``other``.

    Raise a :class:`RuntimeError` if ``other`` is not suspended.

    """
    if other._next_event[0] is not EVT_SUSPEND:
        raise RuntimeError('%s is not suspended.' % other)

    other._next_event = None
    sim._schedule(other, EVT_RESUME)


def interrupt_on(sim, other):
    """Register at ``other`` to receive an interrupt when it terminates."""
    proc = sim._active_proc

    if other.is_alive:
        other._observers.append(proc)
    else:
        # We cannot just schedule an interrupt event, because that would
        # break the following hold(). Since hold() is much more often
        # used, we fix that problem here  by starting a small helper
        # process.
        def interruptor(context, victim):
            yield context.hold(0)
            context.interrupt(victim)

        sim.start(interruptor, proc)


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
        """Return the currently active process."""
        return self._sim._active_proc

    @property
    def now(self):
        """Return the current simulation time."""
        return self._sim._now


class Simulation(object):
    """This is SimPy's central class and actually performs a simulation.

    It manages the processes' _events and coordinates their execution.

    Processes interact with the simulation via a simulation
    :class:`Context` object that is passed to every process when it is
    started.

    """
    # The following functions are all bound to a Simulation instance and
    # are later set as attributes to the Context and Simulation
    # instances.
    # Since some of these methods are shared between the Simulation and
    # Context and some are exclusively for the Context, they are defined
    # as module level Functions to keep the Simulation and Context APIs
    # clean.
    context_funcs = (start, exit, hold, interrupt, suspend, resume,
                     interrupt_on)
    simulation_funcs = (start, interrupt, resume)

    def __init__(self):
        self._events = []

        self._pid = count()
        self._eid = count()
        self._active_proc = None
        self._now = 0

        # Instantiate the context and bind it to the simulation.
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
        """Return the current simulation time."""
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

        Raise an :class:`IndexError` if no valid event is on the heap.

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
            raise ValueError('Invalid yield value: %s' % target)

        # else: target is event

        # Schedule concurrent interrupts.
        if interrupts:
            proc._next_event = None
            self._schedule(proc, EVT_INTERRUPT, interrupts.pop(0))

        self._active_proc = None

    def step_dt(self, delta_t=1):
        """Execute all events that occur within the next *delta_t*
        units of simulation time.

        """
        if delta_t <= 0:
            raise ValueError('delta_t(=%s) should be a number > 0.' % delta_t)

        until = self._now + delta_t
        while self.peek() < until:
            self.step()

    def simulate(self, until=Infinity):
        """Shortcut for ``while sim.peek() < until: sim.step()``."""
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

        Raise a :class:`RuntimeError` if ``proc`` already has an event
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
            observer._next_event = None
            self._schedule(observer, EVT_INTERRUPT, Interrupt(proc))
