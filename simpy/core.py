"""
This module contains the implementation of SimPy's core classes. The
most important ones are directly importable via :mod:`simpy`.

- :class:`Environment`: SimPy's central class. It contains the
  simulation's state and lets the PEMs interact with it (i.e., schedule
  events).

- :class:`~simpy.core.Process`: This class represents a PEM while
  it is executed in an environment. An instance of it is returned by
  :meth:`Environment.start()`. It inherits :class:`Event`.

- :class:`Interrupt`: This exception is thrown into a process if it gets
  interrupted by another one.

- :class:`Event`: A simple event that can be used to implement things
  like shared resources.

- :class:`Timeout`: Can be yielded by a PEM to hold its state or wait
  for a certain amount of time.

- :class:`Condition`: Groups multiple events and is triggered if a
  custom condition on them evaluates to true. There are two default
  evaluation functions (:func:`all_events()` and :func:`any_event()`
  that are used for :class:`Event`'s implementation of ``__and__`` and
  ``__or__``.

This module also contains a few functions to simulate an
:class:`Environment`: :func:`peek()`, :func:`step()` and the shortcut
:func:`simulate()`.

"""
from heapq import heappush, heappop
from inspect import isgenerator
from itertools import count
from numbers import Number


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
    __slots__ = ('callbacks', 'env', '_triggered', 'defused')

    def __init__(self, env):
        self.callbacks = []
        """List of functions that are called when the event is
        processed."""
        self.env = env
        """The :class:`Environment` the event lives in."""
        self._triggered = False

    def __str__(self):
        return '%s()' % self.__class__.__name__

    def __repr__(self):
        return '<%s at 0x%x>' % (self, id(self))

    @property
    def triggered(self):
        """Becomes ``True`` if the event has been triggered and its callbacks
        are about to be invoked."""
        return self._triggered

    @property
    def processed(self):
        """Becomes ``True`` if the event has been processed (e.g., its
        callbacks have been invoked)."""
        return self.callbacks is None

    def succeed(self, value=None):
        """Schedule the event and mark it as successful.

        You can optionally pass an arbitrary ``value`` that will be sent
        into processes waiting for that event.

        Raise a :exc:`RuntimeError` if this event has already been
        scheduled.

        """
        self.env._schedule(EVT_RESUME, self, SUCCEED, value)

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
        self.env._schedule(EVT_RESUME, self, FAIL, exception)

    def __and__(self, other):
        return Condition(self.env, all_events, [self, other])

    def __or__(self, other):
        return Condition(self.env, any_event, [self, other])


class Condition(Event):
    """A *Condition* event groups several ``events`` and is triggered if
    a given condition (implemented by the ``evaluate`` function) becomes
    true.

    The result of the condition is a dictionary that maps the input
    events to their respective results. It only contains entries for
    those events that occurred until the condition was met.

    If one of the ``events`` fails, the condition also fails and
    forwards the exception of the failing event.

    The ``evaluate`` function receives the list of target events and the
    dictionary with all results currently available. If it returns
    ``True``, the condition is scheduled. SimPy provides the
    :func:`all_events()` and :func:`any_event()` functions that are used
    for the implementation of *and* (``&``) and *or* (``|``) of all
    SimPy event types.

    Since condition are normal events, too, they can also be used as
    sub- or nested conditions.

    """
    __slots__ = ('callbacks', 'env', '_evaluate', '_results', '_events',
                 '_sub_conditions')

    def __init__(self, env, evaluate, events):
        Event.__init__(self, env)
        self._evaluate = evaluate
        self._results = {}
        self._events = []
        self._sub_conditions = []

        for event in events:
            self._add_event(event)

        # Register a callback which will update the value of this
        # condition once it is being processed.
        self.callbacks.append(self._collect_results)

    def __str__(self):
        return '%s(%s, [%s])' % (self.__class__.__name__,
                self._evaluate.__name__,
                ', '.join([repr(event) for event in self._events]))

    def _get_results(self):
        """Recursively collects the current results of all nested
        conditions into a flat dictionary."""
        results = dict(self._results)

        for condition in self._sub_conditions:
            if condition in results:
                del results[condition]
            results.update(condition._get_results())

        return results

    def _collect_results(self, event, evt_type, value):
        """Populates the final value of this condition."""
        if evt_type is not FAIL:
            value.update(self._get_results())

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

    def _check(self, event, evt_type, value):
        """Check if the condition was already met and schedule the event
        if so."""
        self._results[event] = value

        if not self._triggered:
            if evt_type is FAIL:
                # Abort if the event has failed.
                event.defused = True
                self.env._schedule(EVT_RESUME, self, FAIL, value)
            elif self._evaluate(self._events, self._results):
                # The condition has been met. Schedule the event with an empty
                # dictionary as value. The _collect_results callback will
                # populate this dictionary once this condition gets processed.
                self.env._schedule(EVT_RESUME, self, SUCCEED, {})

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


def all_events(events, results):
    """Helper for :class:`Condition`. Return ``True`` if there are
    results for all ``events``."""
    return len(events) == len(results)


def any_event(events, results):
    """Helper for :class:`Condition`. Return ``True`` if there is at
    least one result available from ``events``."""
    return len(results) > 0


class Timeout(Event):
    """An event that is scheduled with a certain ``delay`` after its
    creation.

    This event can be used by processes to wait (or hold their state)
    for ``delay`` time steps. It is immediately scheduled at ``env.now
    + delay`` and has thus (in contrast to :class:`Event`) no
    *success()* or *fail()* method.

    """
    __slots__ = ('callbacks', 'env', '_delay', '_value')

    def __init__(self, env, delay, value=None):
        self.callbacks = []
        """List of functions that are called when the event is
        processed."""
        self.env = env
        """The :class:`Environment` the timeout lives in."""
        self._triggered = False

        self._delay = delay
        self._value = value

        if delay < 0:
            raise ValueError('Negative delay %s' % delay)
        env._schedule(EVT_RESUME, self, SUCCEED, value, delay)

    def __str__(self):
        return '%s(%s%s)' % (self.__class__.__name__, self._delay,
                    '' if self._value is None else
                    (', value=' + str(self._value)))


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
    __slots__ = ('callbacks', 'env', '_generator', '_target')

    def __init__(self, env, generator):
        if not isgenerator(generator):
            raise ValueError('%s is not a generator.' % generator)

        self.callbacks = []
        """List of functions that are called when the event is
        processed."""
        self.env = env
        """The :class:`Environment` the process lives in."""
        self._triggered = False

        self._generator = generator

        init = Event(env)
        init.callbacks.append(self._resume)
        env._schedule(EVT_INIT, init, SUCCEED)
        self._target = init

    def __str__(self):
        """Return a string "Process(pem_name)"."""
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
        return not self._triggered

    def interrupt(self, cause=None):
        """Interupt this process optionally providing a ``cause``.

        A process cannot be interrupted if it already terminated.
        A process can also not interrupt itself. Raise
        a :exc:`RuntimeError` in these cases.

        """
        if not self.is_alive:
            raise RuntimeError('%s has terminated and cannot be interrupted.' %
                               self)

        if self is self.env.active_process:
            raise RuntimeError('A process is not allowed to interrupt itself.')

        # Schedule interrupt event
        event = Event(self.env)
        event.callbacks.append(self._resume)
        # Interrupts do not cause the simulation to crash.
        event.defused = True
        self.env._schedule(EVT_INTERRUPT, event, FAIL, Interrupt(cause))

    def _resume(self, event, success, value):
        """Get the next event from this process and register as a callback.

        If the PEM generator exits or raises an exception, terminate
        this process. Also schedule this process to notify all
        registered callbacks, that the process terminated.

        """
        # Ignore dead processes. Multiple concurrently scheduled
        # interrupts cause this situation. If the process dies while
        # handling the first one, the remaining interrupts must be
        # discarded.
        if self._triggered:
            return

        # If the current target (e.g. an interrupt) isn't the one the process
        # expects, remove it from the original events joiners list.
        if self._target is not event:
            self._target.callbacks.remove(self._resume)

        # Mark the current process as active.
        self.env._active_proc = self

        # Get next event from process
        try:
            if success:
                next_evt = self._generator.send(value)
            else:
                # The process has no choice but to handle the failed event (or
                # fail itself).
                event.defused = True
                next_evt = self._generator.throw(value)
        except StopIteration as e:
            # Process has terminated.
            evt_type = SUCCEED
            result = e.args[0] if len(e.args) else None
        except BaseException as e:
            # Process has failed.
            evt_type = FAIL
            result = type(e)(*e.args)
            result.__cause__ = e
        else:
            # Process returned another event to wait upon.
            try:
                # Be optimistic and blindly try to register the process as a
                # callbacks.
                next_evt.callbacks.append(self._resume)
                self._target = next_evt
            except AttributeError:
                # Our optimism didn't work out, figure out what went wrong and
                # inform the user.
                if (hasattr(next_evt, 'callbacks') and
                        next_evt.callbacks is None):
                    msg = 'Event already occured "%s"' % next_evt
                else:
                    msg = 'Invalid yield value "%s"' % next_evt

                descr = _describe_frame(self._generator.gi_frame)
                error = RuntimeError('\n%s%s' % (descr, msg))
                # Drop the AttributeError as the cause for this exception.
                error.__cause__ = None
                raise error

            self.env._active_proc = None
            return

        # The process terminated. Schedule this event.
        # FIXME Setting target to None is only needed for resources.
        self._target = None
        self.env._schedule(EVT_RESUME, self, evt_type, result)
        self.env._active_proc = None


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

        From Python 3.3, you can use ``return result`` instead.

        """
        raise StopIteration(result)

    def event(self):
        """Create and return a new :class:`Event`."""
        return Event(self)

    suspend = event
    """Convenience method. Alias for :meth:`~event`."""

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

    def _schedule(self, evt_type, event, succeed, value=None, delay=0):
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
        if event._triggered:
            raise RuntimeError('Event %s has already been triggered' % event)

        event._triggered = True

        heappush(self._events, (
            self._now + delay,
            evt_type,
            next(self._eid),
            succeed,
            event,
            value,
        ))


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

    if succeed == FAIL:
        if not hasattr(event, 'defused') or not event.defused:
            # The event has not been defused by a callback.
            raise value


def simulate(env, until=None):
    """Simulate the environment until the given criterion *until* is met.

    The parameter ``until`` specifies when the simulation ends.

    - If it is ``None`` (which is the default) the simulation will only
      stop if there are no further events.

    - If it is an :class:`Event` the simulation will stop once this
      event has happened.

    - If it is a number the simulation will stop when the simulation

      time reaches *until*. (*Note:* Internally, an event is created, so
      the simulation time will be exactly *until* afterwards. No other
      events scheduled for *until* will be processed, though---as it
      is at the very beginning of the simulation.)

    """
    if until is None:
        until = env.event()
    elif isinstance(until, Number):
        if until <= env.now:
            raise ValueError('until(=%s) should be > the current simulation '
                             'time.' % until)
        delay = until - env.now
        until = env.event()
        # EVT_INIT schedules "until" before all other events for that time.
        env._schedule(EVT_INIT, until, SUCCEED, delay=delay)
    elif not isinstance(until, Event):
        raise ValueError('"until" must be None, a number or an event, '
                         'but not "%s"' % until)

    events = env._events
    while events and until.callbacks is not None:
        step(env)


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
