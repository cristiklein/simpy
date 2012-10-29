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
(
    EVT_INIT,       # First event after a proc was started
    EVT_INTERRUPT,  # Throw an interrupt into the PEG
    EVT_RESUME,     # Default event, send value into the PEG
) = range(3)

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
    __slots__ = ('processes', '_env', '_activated')

    def __init__(self, env):
        self._env = env
        self._activated = False
        self.processes = []

    @property
    def is_alive(self):
        """``False`` if the PEG stopped."""
        return self.processes is not None

    @property
    def is_activated(self):
        return self._activated

    def activate(self, succeed=True, value=None):
        if self._activated:
            raise RuntimeError('Event %s has already been activated.' % self)
        _schedule(self._env, EVT_RESUME, self, succeed, value)
        self._activated = True

    def succeed(self, value=None):
        self.activate(True, value)

    def fail(self, value=None):
        self.activate(False, value)


class Process(Event):
    """A *Process* is a wrapper for instantiated PEMs.

    A Processes has a process event generator (``peg`` -- the generator
    that the PEM returns) and a reference to its :class:`Environment`
    ``env``. It also contains internal and external status information.
    It is also used for process interaction, e.g., for interruptions.

    An instance of this class is returned by
    :meth:`Environment.start()`.

    """
    __slots__ = ('processes', '_env', '_activated',
                 'name', '_peg', '_target')

    def __init__(self, env, peg):
        super(Process, self).__init__(env)
        self.name = peg.__name__
        """The process name."""

        self._peg = peg
        self._target = None

    def __repr__(self):
        """Return a string "Process(pem_name)"."""
        return '%s(%s)' % (self.__class__.__name__, self.name)

    def interrupt(self, cause=None):
        """Interupt this process optionally providing a ``cause``.

        A process cannot be interrupted if it is suspended (and has no
        event activated) or if it was just initialized and could not
        issue a *hold* yet. Raise a :exc:`RuntimeError` in both cases.

        If ``cause`` is an instance of an exception, it will be directly
        thrown into the process. If not, an :class:`Interrupt` will be
        thrown.

        """
        if not self.is_alive:
            raise RuntimeError('%s has terminated and cannot be interrupted.' %
                               self)

        # Unsubscribe the event we were waiting for
        if self._target:
            self._target.processes.remove(self)
            self._target = None

        # Schedule interrupt event
        event = Event(self._env)
        event.processes.append(self)
        _schedule(self._env, EVT_INTERRUPT, event, succeed=False,
                  value=Interrupt(cause))
        event._activated = True


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

        Raise a :exc:`ValueError` if ``peg`` is not a generator.

        """
        if not isgenerator(peg):
            raise ValueError('PEG %s is not a generator.' % peg)

        proc = Process(self, peg)

        event = Event(self)
        event.processes.append(proc)
        _schedule(self, EVT_INIT, event, succeed=True)
        event._activated = True

        return proc

    def exit(self, result=None):
        """Stop the current process, optionally providing a ``result``.

        The ``result`` is sent to processes waiting for the current
        process and can also be obtained via :attr:`Process.result`.

        """
        raise StopIteration(result)

    def hold(self, delta_t=Infinity, value=None):
        # TODO: rename?
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

        event = Event(self)
        _schedule(self, EVT_RESUME, event, succeed=True, value=value,
                  at=(self._now + delta_t))
        event._activated = True

        return event


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
    if env._active_proc:
        raise RuntimeError('step() was called from within step().'
                           'Something went horribly wrong.')

    env._now, evt_type, eid, succeed, event, value = heappop(env._events)

    # Mark event as processed
    processes, event.processes = event.processes, None

    for proc in processes:
        # Ignore terminated processes
        if not proc.is_alive:
            continue

        env._active_proc = proc
        proc._target = None

        # Get next event from process
        try:
            new_event = proc._peg.send(value) if succeed else \
                        proc._peg.throw(value)

        # proc has terminated
        except StopIteration as si:
            proc.activate(succeed=True, value=si.args[0] if si.args else None)
            continue  # Don't need to check a new event

        # proc raised an error. Try to forward it or re-raise it.
        except BaseException as err:
            if not proc.processes:
                raise err
            proc.activate(succeed=False, value=err)
            continue  # Don't need to check a new event

        # Check yielded event
        try:
            if new_event.is_alive:
                new_event.processes.append(proc)
                proc._target = new_event
            else:
                proc._peg.throw(RuntimeError('%s is not alive.' % new_event))

        except AttributeError:
            proc._peg.throw(ValueError('Invalid yield value: %s' % new_event))

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


def _schedule(env, evt_type, event, succeed, value=None, at=None):
    """Schedule a new event for process ``proc``.

    ``evt_type`` should be one of the ``EVT_*`` constants defined on
    top of this module.

    The optional ``value`` will be sent into the PEG when the event is
    processed.

    The event will be activated at the simulation time ``at`` or at the
    current time if no value is provided.

    Raise a :exc:`RuntimeError` if ``proc`` already has an event
    activated.

    """
    # Don't put events activated for "Infinity" onto the heap,
    # because the will never be popped.
    if at is Infinity:
        return

    if at is None:
        at = env._now

    heappush(env._events, (at, evt_type, next(env._eid), succeed, event,
                           value))
