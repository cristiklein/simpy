"""
This module contains the implementation of SimPy's core classes. The
most important ones are directly importable via :mod:`simpy`.

"""
import types
from heapq import heappush, heappop
from inspect import isgenerator
from itertools import count

from simpy._compat import PY2

if PY2:
    import sys


Infinity = float('inf')  # Convenience alias for infinity

PENDING = object()       # Unique object to identify pending values of events

HIGH_PRIORITY = 0        # Priority of interrupts and Initialize events
DEFAULT_PRIORITY = 1     # Default priority used by events
LOW_PRIORITY = 2         # Priority of timeouts


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

    def __str__(self):
        return '%s(%r)' % (self.__class__.__name__, self.cause)

    @property
    def cause(self):
        """Property that returns the cause of an interrupt or ``None``
        if no cause was passed."""
        return self.args[0]


class Event(object):
    """Base class for all events.

    Every event is bound to an :class:`Environment` ``env`` and has a
    list of ``callbacks`` that are called when the event is processed.

    A callback can be any callable that accepts the following arguments:

    - *event:* The :class:`Event` instance the callback was registered
      at.
    - *success:* Boolean that indicates if the event was successful.
      A process that raised an uncaught exception might for example
      cause an unsuccessful (failed) event.
    - *value:* An event can optionally send an arbitrary value. It
      defaults to ``None``.

    You can add callbacks by appending them to the ``callbacks``
    attribute of an event.

    This class also implements ``__and__()`` (``&``) and ``__or__()``
    (``|``). If you concatenate two events using one of these operators,
    a :class:`Condition` event is generated that lets you wait for both
    or one of them.

    """
    def __init__(self, env, value=PENDING, name=None):
        self.callbacks = []
        """List of functions that are called when the event is
        processed."""
        self.env = env
        """The :class:`Environment` the event lives in."""
        self.name = name
        """Optional name for this event. Used for :class:`str` / :func:`repr`
        if not ``None``."""
        self._value = value

    def __repr__(self):
        """Use ``self.name`` if defined or ``self._desc()`` else."""
        if self.name is None:
            return '<%s object at 0x%x>' % (self._desc(), id(self))
        else:
            return self.name

    def _desc(self):
        """Return a string *Event()*."""
        return '%s()' % self.__class__.__name__

    @property
    def triggered(self):
        """Becomes ``True`` if the event has been triggered and its callbacks
        are about to be invoked."""
        return self._value is not PENDING

    @property
    def processed(self):
        """Becomes ``True`` if the event has been processed (e.g., its
        callbacks have been invoked)."""
        return self.callbacks is None

    @property
    def value(self):
        """Return the value of the event if it is available.

        The value is available when the event has been triggered.

        Raise a :exc:`RuntimeError` if the value is not yet available.

        """
        if self._value is PENDING:
            raise RuntimeError('Value of %s is not yet available' % self)
        return self._value

    def trigger(self, event):
        """Triggers the event with value of the provided ``event``.
        
        This method can be used directly as a callback function.
        
        """
        self.ok = event.ok
        self._value = event._value
        self.env.schedule(self, DEFAULT_PRIORITY)

    def succeed(self, value=None):
        """Schedule the event and mark it as successful.

        You can optionally pass an arbitrary ``value`` that will be sent
        into processes waiting for that event.

        Raise a :exc:`RuntimeError` if this event has already been
        scheduled.

        """
        if self._value is not PENDING:
            raise RuntimeError('%s has already been triggered' % self)

        self.ok = True
        self._value = value
        self.env.schedule(self, DEFAULT_PRIORITY)
        return self

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
        if self._value is not PENDING:
            raise RuntimeError('%s has already been triggered' % self)
        self.ok = False
        self._value = exception
        self.env.schedule(self, DEFAULT_PRIORITY)
        return self

    def __and__(self, other):
        return Condition(self.env, all_events, [self, other])

    def __or__(self, other):
        return Condition(self.env, any_event, [self, other])


class Condition(Event):
    """A *Condition* event groups several ``events`` and is triggered if
    a given condition (implemented by the ``evaluate`` function) becomes
    true.

    The value of the condition is a dictionary that maps the input
    events to their respective values. It only contains entries for
    those events that occurred until the condition was met.

    If one of the ``events`` fails, the condition also fails and
    forwards the exception of the failing event.

    The ``evaluate`` function receives the list of target events and the
    dictionary with all values currently available. If it returns
    ``True``, the condition is scheduled. SimPy provides the
    :func:`all_events()` and :func:`any_event()` functions that are used
    for the implementation of *and* (``&``) and *or* (``|``) of all
    SimPy event types.

    Since condition are normal events, too, they can also be used as
    sub- or nested conditions.

    """
    def __init__(self, env, evaluate, events, name=None):
        Event.__init__(self, env, name=name)
        self._evaluate = evaluate
        self._interim_values = {}
        self._events = []
        self._sub_conditions = []

        for event in events:
            self._add_event(event)

        # Register a callback which will update the value of this
        # condition once it is being processed.
        self.callbacks.append(self._collect_values)

    def _desc(self):
        """Return a string *Condition(and_or_or, [events])*."""
        return '%s(%s, %s)' % (self.__class__.__name__,
                               self._evaluate.__name__, self._events)

    def _get_values(self):
        """Recursively collects the current values of all nested
        conditions into a flat dictionary."""
        values = dict(self._interim_values)

        for condition in self._sub_conditions:
            if condition in values:
                del values[condition]
            values.update(condition._get_values())

        return values

    def _collect_values(self, event):
        """Populates the final value of this condition."""
        if event.ok:
            self._value.update(self._get_values())

    def _add_event(self, event):
        """Add another event to the condition."""
        if self.env != event.env:
            raise RuntimeError('It is not allowed to mix events from '
                               'different environments')
        if self.callbacks is None:
            raise RuntimeError('Event %s has already been triggered' % self)
        if event.callbacks is None:
            raise RuntimeError('Event %s has already been triggered' % event)

        if type(event) is Condition:
            self._sub_conditions.append(event)

        self._events.append(event)
        event.callbacks.append(self._check)

        return self

    def _check(self, event):
        """Check if the condition was already met and schedule the event
        if so."""
        self._interim_values[event] = event._value

        if self._value is PENDING:
            if not event.ok:
                # Abort if the event has failed.
                event.defused = True
                self.fail(event._value)
            elif self._evaluate(self._events, self._interim_values):
                # The condition has been met. Schedule the event with an empty
                # dictionary as value. The _collect_values callback will
                # populate this dictionary once this condition gets processed.
                self.succeed({})

    def __iand__(self, other):
        if self._evaluate is not all_events:
            # Use self.__and__
            return NotImplemented

        return self._add_event(other)

    def __ior__(self, other):
        if self._evaluate is not any_event:
            # Use self.__or__
            return NotImplemented

        return self._add_event(other)


def all_events(events, values):
    """Helper for :class:`Condition`. Return ``True`` if there are
    values for all ``events``."""
    return len(events) == len(values)


def any_event(events, values):
    """Helper for :class:`Condition`. Return ``True`` if there is at
    least one value available from ``events``."""
    return len(values) > 0


class Timeout(Event):
    """An event that is scheduled with a certain ``delay`` after its
    creation.

    This event can be used by processes to wait (or hold their state)
    for ``delay`` time steps. It is immediately scheduled at ``env.now
    + delay`` and has thus (in contrast to :class:`Event`) no
    *success()* or *fail()* method.

    """
    def __init__(self, env, delay, value=None, name=None):
        if delay < 0:
            raise ValueError('Negative delay %s' % delay)
        # NOTE: The following initialization code is inlined from
        # Event.__init__() for performance reasons.
        self.callbacks = []
        self.env = env
        self.name = name
        self._delay = delay
        self.ok = True
        self._value = value
        env.schedule(self, LOW_PRIORITY, delay)

    def _desc(self):
        """Return a string *Timeout(delay[, value=value])*."""
        return '%s(%s%s)' % (self.__class__.__name__, self._delay,
                             '' if self._value is None else
                             (', value=%s' % self._value))


class Initialize(Event):
    """Initializes a process."""
    def __init__(self, env, process):
        self.env = env
        self.name = None
        self.ok = True
        self._value = None
        self.callbacks = [process._resume]
        env.schedule(self, HIGH_PRIORITY)


class Process(Event):
    """A *Process* is a wrapper for instantiated PEMs during their
    execution.

    A Processes has a generator (the generator that the PEM returns) and
    a reference to its :class:`Environment` ``env``. It also contains
    internal and external status information.  It is also used for
    process interaction, e.g., for interruptions.

    ``Process`` inherits :class:`Event`. You can thus wait for the
    termination of a process by simply yielding it from your PEM.

    An instance of this class is returned by
    :meth:`Environment.start()`.

    """
    def __init__(self, env, generator, name=None):
        if not isgenerator(generator):
            raise ValueError('%s is not a generator.' % generator)

        # NOTE: The following initialization code is inlined from
        # Event.__init__() for performance reasons.
        self.callbacks = []
        self.env = env
        self.name = name
        self._generator = generator
        self._value = PENDING

        # Schedule the start of the execution of the process.
        self._target = Initialize(env, self)

    def _desc(self):
        """Return a string *Process(pem_name)*."""
        return '%s(%s)' % (self.__class__.__name__, self._generator.__name__)

    @property
    def target(self):
        """The event that the process is currently waiting for.

        May be ``None`` if the process was just started or interrupted
        and did not yet yield a new event.

        """
        return self._target

    @property
    def is_alive(self):
        """``True`` until the event has been processed."""
        return self._value is PENDING

    def interrupt(self, cause=None):
        """Interupt this process optionally providing a ``cause``.

        A process cannot be interrupted if it already terminated.
        A process can also not interrupt itself. Raise
        a :exc:`RuntimeError` in these cases.

        """
        if self._value is not PENDING:
            raise RuntimeError('%s has terminated and cannot be interrupted.' %
                               self)

        if self is self.env.active_process:
            raise RuntimeError('A process is not allowed to interrupt itself.')

        # Schedule interrupt event
        event = self.env.event(Interrupt(cause))
        event.ok = False
        # Interrupts do not cause the simulation to crash.
        event.defused = True
        event.callbacks.append(self._resume)
        self.env.schedule(event, HIGH_PRIORITY)

    def _resume(self, event):
        """Get the next event from this process and register as a callback.

        If the PEM generator exits or raises an exception, terminate
        this process. Also schedule this process to notify all
        registered callbacks, that the process terminated.

        """
        # Ignore dead processes. Multiple concurrently scheduled
        # interrupts cause this situation. If the process dies while
        # handling the first one, the remaining interrupts must be
        # discarded.
        if self._value is not PENDING:
            return

        # If the current target (e.g. an interrupt) isn't the one the process
        # expects, remove it from the original events joiners list.
        if self._target is not event:
            self._target.callbacks.remove(self._resume)

        # Mark the current process as active.
        self.env._active_proc = self

        while True:
            # Get next event from process
            try:
                if event.ok:
                    event = self._generator.send(event._value)
                else:
                    # The process has no choice but to handle the failed event
                    # (or fail itself).
                    event.defused = True
                    event = self._generator.throw(event._value)
            except StopIteration as e:
                # Process has terminated.
                event = None
                self.ok = True
                self._value = e.args[0] if len(e.args) else None
                self.env.schedule(self, DEFAULT_PRIORITY)
                break
            except BaseException as e:
                # Process has failed.
                event = None
                self.ok = False
                self._value = type(e)(*e.args)
                self._value.__cause__ = e
                if PY2:
                    self._value.__traceback__ = sys.exc_info()[2]
                self.env.schedule(self, DEFAULT_PRIORITY)
                break

            # Process returned another event to wait upon.
            try:
                # Be optimistic and blindly access the callbacks attribute.
                if event.callbacks is not None:
                    # The event has not yet been triggered. Register callback
                    # to resume the process if that happens.
                    event.callbacks.append(self._resume)
                    break
            except AttributeError:
                # Our optimism didn't work out, figure out what went wrong and
                # inform the user.
                if not hasattr(event, 'callbacks'):
                    msg = 'Invalid yield value "%s"' % event

                descr = _describe_frame(self._generator.gi_frame)
                error = RuntimeError('\n%s%s' % (descr, msg))
                # Drop the AttributeError as the cause for this exception.
                error.__cause__ = None
                raise error

        self._target = event
        self.env._active_proc = None


class EmptySchedule(Exception):
    """Thrown by a :class:`Scheduler` if its :attr:`~Scheduler.queue` is
    empty."""
    pass


class Scheduler(object):
    """Schedulers manage the event queue of an :class:`Environment`.

    They schedule/enqueue new events and pop events from the queue. They also
    manage the current simulation time.

    """
    def __init__(self, env, initial_time):
        self.env = env
        self.now = initial_time
        self.queue = []
        self._eid = count()

    def schedule(self, event, priority=DEFAULT_PRIORITY, delay=0):
        """Schedule an *event* with a given *priority* and a *delay*."""
        heappush(self.queue, (self.now + delay, priority, next(self._eid),
                              event))

    def peek(self):
        """Get the time of the next scheduled event. Return ``Infinity`` if the
        event queue is empty."""
        try:
            return self.queue[0][0]
        except IndexError:
            return Infinity

    def pop(self):
        """Remove and return the next event from the queue as ``(now, event)``.

        Raise :exc:`EmptySchedule` if the schedule is empty.

        """
        try:
            self.now, _, _, event = heappop(self.queue)
            return event
        except IndexError:
            raise EmptySchedule()


class BaseEnvironment(object):
    """Base class for an environment, which schedules and executes events and
    processes. 

    """
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self._active_proc = None

        self.schedule = self.scheduler.schedule
        self.pop = self.scheduler.pop

    @property
    def active_process(self):
        """Property that returns the currently active process."""
        return self._active_proc

    @property
    def now(self):
        """Property that returns the current simulation time."""
        return self.scheduler.now

    def exit(self, value=None):
        """Stop the current process, optionally providing a ``value``.

        The ``value`` is sent to processes waiting for the current
        process.

        From Python 3.3, you can use ``return value`` instead.

        """
        raise StopIteration(value)

    def step(env):
        """Process the next event for the Environment ``env``.

        Raise an :exc:`EmptySchedule` if no valid event is on the heap.

        """
        event = env.pop()

        # Process callbacks of the event.
        for callback in event.callbacks:
            callback(event)
        event.callbacks = None

        if not event.ok:
            # The event has failed, check if it is defused. Raise the value if not.
            if not hasattr(event, 'defused'):
                raise event._value


class Environment(BaseEnvironment):
    """The *environment* contains the simulation state and provides a
    basic API for processes to interact with it.

    """
    def __init__(self, initial_time=0, scheduler=None):
        if scheduler is None:
            scheduler = Scheduler(self, initial_time)
        super(Environment, self).__init__(scheduler)

        self.event = types.MethodType(Event, self)
        self.suspend = types.MethodType(Event, self)
        self.timeout = types.MethodType(Timeout, self)
        self.process = types.MethodType(Process, self)
        self.start = types.MethodType(Process, self)

    def peek(self):
        """Return the time at which the next event is scheduled or ``inf`` if
        the event queue is empty.

        """
        return self.scheduler.peek()

    def simulate(self, until=None):
        """Executes events until the given criterion *until* is met.

        - If it is ``None`` (which is the default) the execution will only
          stop if there are no further events.

        - If it is an :class:`Event` the execution will stop once this
          event has been triggered.

        - If it can be converted to a number the execution will stop when the
          simulation time reaches *until*. (*Note:* Internally, an event is
          created, so the simulation time will be exactly *until* afterwards.
          No other events scheduled for *until* will be processed, though---as
          it is at the very beginning of the simulation.)

        """
        if until is None:
            until = Event(self)
        elif not isinstance(until, Event):
            at = float(until)

            if at <= self.now:
                raise ValueError('until(=%s) should be > the current '
                        'simulation time.' % at)

            # Schedule the event with before all regular timeouts.
            until = Event(self)
            until._value = None
            self.schedule(until, HIGH_PRIORITY, at - self.now)

        until.callbacks.append(_stop_simulate)

        try:
            while True:
                self.step()
        except EmptySchedule:
            pass

        return until.value if until.triggered else None


def _describe_frame(frame):
    """Prints filename, linenumber and function name of a stackframe."""
    filename, name = frame.f_code.co_filename, frame.f_code.co_name
    lineno = frame.f_lineno

    with open(filename) as f:
        for no, line in enumerate(f):
            if no + 1 == lineno:
                break

    return '  File "%s", line %d, in %s\n    %s\n' % (filename, lineno, name,
                                                      line.strip())


def _stop_simulate(event):
    """Used as callback in :func:`simulate()` to stop the simulation when the
    *until* event occured."""
    raise EmptySchedule()
