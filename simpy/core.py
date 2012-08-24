from heapq import heappush, heappop
from itertools import count
from types import GeneratorType

from simpy.exceptions import Interrupt, Failure


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


class Process(object):
    """A *Process* is a wrapper for instantiated PEMs.

    A Processes needs a unique process ID (*pid*) and a process event
    generator (*peg* -- the generator that the PEM returns).

    The *Process* class contains internal and external status
    information. It is also used for process interaction, e.g., for
    interruptions.

    """
    __slots__ = ('pid', 'peg', 'state', 'result', 'is_terminated',
                 '_next_event', '_joiners', '_signallers', '_interrupts',
                 '_terminated')

    def __init__(self, pid, peg):
        self.pid = pid
        self.peg = peg

        self.state = None  # FIXME: Remove or make private?
        self.result = None

        self._next_event = None
        self._joiners = []
        self._signallers = []  # FIXME: Rename to _observers?
        self._interrupts = []

        self._terminated = False

    @property
    def is_terminated(self):
        """``True`` if the PEG stopped."""
        return self._terminated

    def __repr__(self):
        """Return a string "Process(pid, pem_name)"."""
        return '%s(%s, %s)' % (self.__class__.__name__, self.pid,
                               self.peg.__name__)


def start(sim, pem, *args, **kwargs):
    """Start a new process for ``pem``.

    Pass *simulation context* and, optionally, ``*args`` and
    ``**kwargs`` to the PEM.

    If ``pem`` is not a generator function, raise a :class`ValueError`.

    """
    peg = pem(sim.context, *args, **kwargs)
    if type(peg) is not GeneratorType:
        raise ValueError('PEM %s is not a generator function.' % pem)

    proc = Process(next(sim.pid), peg)
    sim._schedule(proc, EVT_INIT)

    return proc


def exit(sim, result=None):
    """Stop the current process, optinally providing a ``result``.

    The ``result`` is sent to processes waiting for the current process
    and can also be obtained via :attr:`Process.result`.

    """
    sim.active_proc.result = result
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

    sim._schedule(sim.active_proc, EVT_RESUME, at=(sim._now + delta_t))

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

    # This is the first interrupt, so schedule it.
    if not interrupts:
        other._next_event = None
        sim._schedule(other, EVT_INTERRUPT)

    interrupts.append(cause)


def suspend(sim):
    """Suspend the current process by deleting all future events.

    A suspended process needs to be resumed (see
    :class:`Context.resume`) by another process to get active again.

    Raise a :class:`RuntimeError` if the process has already an event
    scheduled.

    """
    sim._schedule(sim.active_proc, EVT_SUSPEND)

    return Event


def resume(sim, other):
    """Resume the suspended process ``other``.

    Raise a :class:`RuntimeError` if ``other`` is not suspended.

    """
    if other._next_event[0] is not EVT_SUSPEND:
        raise RuntimeError('%s is not suspended.' % other)

    other._next_event = None
    sim._schedule(other, EVT_RESUME)


def signal(sim, other):
    """Register at ``other`` to receive an interrupt when it terminates."""
    # FIXME: Rename to "monitor" or "observe"?
    proc = sim.active_proc

    if other.is_terminated:
        sim._schedule(proc, EVT_INTERRUPT, Interrupt(other))
    else:
        other._signallers.append(proc)


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
        return self._sim.active_proc

    @property
    def now(self):
        """Return the current simulation time."""
        return self._sim._now


class Simulation(object):
    """This is SimPy's central class and actually performs a simulation.

    It manages the processes' events and coordinates their execution.

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
    context_funcs = (start, exit, hold, interrupt, suspend, resume, signal)
    simulation_funcs = (start, interrupt, resume)

    def __init__(self):
        # FIXME: Make events, pid, eid, active_proc and context private.
        self.events = []

        self.pid = count()
        self.eid = count()
        self.active_proc = None
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

        heappush(self.events, (at, next(self.eid), proc, proc._next_event))

    def _join(self, proc):
        """Notify all registered processes that the process ``proc``
        terminated.

        """
        joiners = proc._joiners
        signallers = proc._signallers

        # FIXME: Remove this and directly raise exceptions from
        # processes. Forwarding of exceptions can still be done manually
        # if you really need this (which I doubt)
        if proc.state == STATE_FAILED:
            # Raise the exception of a crashed process if there is no
            # other process to handle it.
            if not joiners and not signallers:
                raise proc.result.__cause__

        if joiners:
            for joiner in joiners:
                if joiner.is_terminated:  # FIXME: Can this happen?
                    continue
                evt = EVT_INTERRUPT if proc.state == STATE_FAILED else EVT_RESUME
                self._schedule(joiner, evt, proc.result)

        if signallers:
            for signaller in signallers:
                if signaller.is_terminated:
                    continue
                self._schedule(signaller, EVT_INTERRUPT, Interrupt(proc))

    def peek(self):
        """Return the time of the next event or ``inf`` if the event
        queue is empty.

        """
        try:
            while True:
                # Pop all removed events from the queue
                # self.events[0][3] is the scheduled event
                # self.events[0][2] is the corresponding proc
                if self.events[0][3] is self.events[0][2]._next_event:
                    break
                heappop(self.events)

            return self.events[0][0]  # time of first event

        except IndexError:
            return Infinity

    def step(self):
        """Get and process the next event.

        Raise an :class:`IndexError` if no valid event is on the heap.

        """
        # FIXME: Is it really possible to call step() from within
        # step()? I think not ...
        assert self.active_proc is None

        # Get the next valid event from the heap
        while True:
            self._now, eid, proc, evt = heappop(self.events)

            # Break from the loop if we find a valid event.
            if evt is proc._next_event:
                break

        self.active_proc = proc

        evt_type, value = evt
        proc._next_event = None
        interrupts = proc._interrupts

        # Get next event from process
        try:
            if evt_type is EVT_INTERRUPT:
                cause = interrupts.pop(0)
                target = proc.peg.throw(Interrupt(cause))
            else:
                target = proc.peg.send(value)

        except StopIteration:
            # Process has terminated.
            proc._terminated = True
            proc.state = STATE_SUCCEEDED
            self._join(proc)
            self.active_proc = None
            return
        except BaseException as e:
            # TODO: Remove this
            # Process has failed.
            proc.state = STATE_FAILED
            proc.result = Failure()
            proc.result.__cause__ = e
            self._join(proc)
            self.active_proc = None
            return

        # Check what was yielded
        if type(target) is Process:
            # TODO The stacktrace won't show the position in the pem where this
            # exception occured. Maybe throw the assertion error into the pem?
            assert proc._next_event is None, 'Next event already scheduled!'

            # Add this process to the list of waiters.
            if target.is_terminated:
                # FIXME This context switching is ugly.
                prev, self.active_proc = self.active_proc, target
                # Process has already terminated. Resume as soon as possible.
                evt = EVT_INTERRUPT if target.state == STATE_FAILED else EVT_RESUME
                self._schedule(proc, evt, target.result)
                self.active_proc = prev
            else:
                # FIXME This is a bit ugly. Because next_event cannot be
                # None this stub event is used. It will never be executed
                # because it isn't scheduled. This is necessary for
                # interrupt handling.
                proc._next_event = (EVT_RESUME, None)
                target._joiners.append(proc)

        elif target is not Event:
            raise ValueError('Invalid yield value: %s' % target)

        # else: target is event

        # Schedule concurrent interrupts.
        if interrupts:
            proc._next_event = None
            self._schedule(proc, EVT_INTERRUPT)

        self.active_proc = None

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
