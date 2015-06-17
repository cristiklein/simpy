"""
This module contains the basic event types used in SimPy.

The base class for all events is :class:`Event`. Though it can be directly
used, there are several specialized subclasses of it.

.. autosummary::

    ~simpy.events.Event
    ~simpy.events.Timeout
    ~simpy.events.Process
    ~simpy.events.AnyOf
    ~simpy.events.AllOf

This module also defines the :exc:`Interrupt` exception.

"""
from inspect import isgenerator

from simpy._compat import PY2

if PY2:
    import sys


PENDING = object()
"""Unique object to identify pending values of events."""

URGENT = 0
"""Priority of interrupts and process initialization events."""
NORMAL = 1
"""Default priority used by events."""


class Event(object):
    """An event that may happen at some point in time.

    An event

    - may happen (:attr:`triggered` is ``False``),
    - is going to happen (:attr:`triggered` is ``True``) or
    - has happened (:attr:`processed` is ``True``).

    Every event is bound to an environment *env* and is initially not
    triggered. Events are scheduled for processing by the environment after
    they are triggered by either :meth:`succeed`, :meth:`fail` or
    :meth:`trigger`. These methods also set the *ok* flag and the *value* of
    the event.

    An event has a list of :attr:`callbacks`. A callback can be any callable.
    Once an event gets processed, all callbacks will be invoked with the event
    as the single argument. Callbacks can check if the event was successful by
    examining *ok* and do further processing with the *value* it has produced.

    Failed events are never silently ignored and will raise an exception upon
    being processed. If a callback handles an exception, it must set *defused*
    flag to ``True`` to prevent this.

    This class also implements ``__and__()`` (``&``) and ``__or__()`` (``|``).
    If you concatenate two events using one of these operators,
    a :class:`Condition` event is generated that lets you wait for both or one
    of them.

    """
    def __init__(self, env):
        self.env = env
        """The :class:`~simpy.core.Environment` the event lives in."""
        self.callbacks = []
        """List of functions that are called when the event is processed."""
        self._value = PENDING

    def __repr__(self):
        """Return the description of the event (see :meth:`_desc`) with the id
        of the event."""
        return '<%s object at 0x%x>' % (self._desc(), id(self))

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
        """The value of the event if it is available.

        The value is available when the event has been triggered.

        Raise a :exc:`AttributeError` if the value is not yet available.

        """
        if self._value is PENDING:
            raise AttributeError('Value of %s is not yet available' % self)
        return self._value

    def trigger(self, event):
        """Trigger the event with the state and value of the provided *event*.
        Return *self* (this event instance).

        This method can be used directly as a callback function to trigger
        chain reactions.

        """
        self.ok = event.ok
        self._value = event._value
        self.env.schedule(self)

    def succeed(self, value=None):
        """Set the event's value, mark it as successful and schedule it for
        processing by the environment. Returns the event instance.

        Raise a :exc:`RuntimeError` if this event has already been triggerd.

        """
        if self._value is not PENDING:
            raise RuntimeError('%s has already been triggered' % self)

        self.ok = True
        self._value = value
        self.env.schedule(self)
        return self

    def fail(self, exception):
        """Set *exception* as the events value, mark it as failed and schedule
        it for processing by the environment. Returns the event instance.

        Raise a :exc:`ValueError` if *exception* is not an :exc:`Exception`.

        Raise a :exc:`RuntimeError` if this event has already been triggered.

        """
        if self._value is not PENDING:
            raise RuntimeError('%s has already been triggered' % self)
        if not isinstance(exception, BaseException):
            raise ValueError('%s is not an exception.' % exception)
        self.ok = False
        self._value = exception
        self.env.schedule(self)
        return self

    def __and__(self, other):
        """Return a :class:`~simpy.events.Condition` that will be triggered if
        both, this event and *other*, have been processed."""
        return Condition(self.env, Condition.all_events, [self, other])

    def __or__(self, other):
        """Return a :class:`~simpy.events.Condition` that will be triggered if
        either this event or *other* have been processed (or even both, if they
        happened concurrently)."""
        return Condition(self.env, Condition.any_events, [self, other])


class Timeout(Event):
    """A :class:`~simpy.events.Event` that gets triggered after a *delay* has
    passed.

    This event is automatically triggered when it is created.

    """
    def __init__(self, env, delay, value=None):
        if delay < 0:
            raise ValueError('Negative delay %s' % delay)
        # NOTE: The following initialization code is inlined from
        # Event.__init__() for performance reasons.
        self.env = env
        self.callbacks = []
        self._value = value
        self._delay = delay
        self.ok = True
        env.schedule(self, NORMAL, delay)

    def _desc(self):
        """Return a string *Timeout(delay[, value=value])*."""
        return '%s(%s%s)' % (self.__class__.__name__, self._delay,
                             '' if self._value is None else
                             (', value=%s' % self._value))


class Initialize(Event):
    """Initializes a process. Only used internally by :class:`Process`.

    This event is automatically triggered when it is created.

    """
    def __init__(self, env, process):
        # NOTE: The following initialization code is inlined from
        # Event.__init__() for performance reasons.
        self.env = env
        self.callbacks = [process._resume]
        self._value = None

        # The initialization events needs to be scheduled as urgent so that it
        # will be handled before interrupts. Otherwise a process whose
        # generator has not yet been started could be interrupted.
        self.ok = True
        env.schedule(self, URGENT)


class Interruption(Event):
    """Immediately schedules an :class:`Interrupt` exception with the given
    *cause* to be thrown into *process*.

    This event is automatically triggered when it is created.

    """
    def __init__(self, process, cause):
        # NOTE: The following initialization code is inlined from
        # Event.__init__() for performance reasons.
        self.env = process.env
        self.callbacks = [self._interrupt]
        self._value = Interrupt(cause)
        self.ok = False
        self.defused = True

        if process._value is not PENDING:
            raise RuntimeError('%s has terminated and cannot be interrupted.' %
                               process)

        if process is self.env.active_process:
            raise RuntimeError('A process is not allowed to interrupt itself.')

        self.process = process
        self.env.schedule(self, URGENT)

    def _interrupt(self, event):
        # Ignore dead processes. Multiple concurrently scheduled interrupts
        # cause this situation. If the process dies while handling the first
        # one, the remaining interrupts must be ignored.
        if self.process._value is not PENDING:
            return

        # A process never expects an interrupt and is always waiting for a
        # target event. Remove the process from the callbacks of the target.
        self.process._target.callbacks.remove(self.process._resume)

        self.process._resume(self)


class Process(Event):
    """Process an event yielding generator.

    A generator (also known as a coroutine) can suspend its execution by
    yielding an event. ``Process`` will take care of resuming the generator
    with the value of that event once it has happened. The exception of failed
    events is thrown into the generator.

    ``Process`` itself is an event, too. It is triggered, once the generator
    returns or raises an exception. The value of the process is the return
    value of the generator or the exception, respectively.

    .. note::

       Python version prior to 3.3 do not support return statements in
       generators. You can use :meth:~simpy.core.Environment.exit() as
       a workaround.

    Processes can be interrupted during their execution by :meth:`interrupt`.

    """
    def __init__(self, env, generator):
        if not isgenerator(generator):
            raise ValueError('%s is not a generator.' % generator)

        # NOTE: The following initialization code is inlined from
        # Event.__init__() for performance reasons.
        self.env = env
        self.callbacks = []
        self._value = PENDING

        self._generator = generator

        # Schedule the start of the execution of the process.
        self._target = Initialize(env, self)

    def _desc(self):
        """Return a string *Process(process_func_name)*."""
        return '%s(%s)' % (self.__class__.__name__, self._generator.__name__)

    @property
    def target(self):
        """The event that the process is currently waiting for.

        Returns ``None`` if the process is dead or it is currently being
        interrupted.

        """
        return self._target

    @property
    def is_alive(self):
        """``True`` until the process generator exits."""
        return self._value is PENDING

    def interrupt(self, cause=None):
        """Interupt this process optionally providing a *cause*.

        A process cannot be interrupted if it already terminated. A process can
        also not interrupt itself. Raise a :exc:`RuntimeError` in these
        cases.

        """
        Interruption(self, cause)

    def _resume(self, event):
        """Resumes the execution of the process with the value of *event*. If
        the process generator exits, the process itself will get triggered with
        the return value or the exception of the generator."""
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

                    # Create an exclusive copy of the exception for this
                    # process to prevent traceback modifications by other
                    # processes.
                    exc = type(event._value)(*event._value.args)
                    exc.__cause__ = event._value
                    if PY2:
                        if hasattr(event._value, '__traceback__'):
                            exc.__traceback__ = event._value.__traceback__
                    event = self._generator.throw(exc)
            except StopIteration as e:
                # Process has terminated.
                event = None
                self.ok = True
                self._value = e.args[0] if len(e.args) else None
                self.env.schedule(self)
                break
            except BaseException as e:
                # Process has failed.
                event = None
                self.ok = False
                tb = e.__traceback__ if not PY2 else sys.exc_info()[2]
                # Strip the frame of this function from the traceback as it
                # does not add any useful information.
                e.__traceback__ = tb.tb_next
                self._value = e
                self.env.schedule(self)
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


class ConditionValue(object):
    """Result of a :class:`~simpy.events.Condition`. It supports convenient
    dict-like access to the triggered events and their values. The events are
    ordered by their occurences in the condition."""

    def __init__(self):
        self.events = []

    def __getitem__(self, key):
        if key not in self.events:
            raise KeyError(str(key))

        return key._value

    def __contains__(self, key):
        return key in self.events

    def __eq__(self, other):
        if type(other) is ConditionValue:
            return self.events == other.events

        return self.todict() == other

    def __repr__(self):
        return '<ConditionValue %s>' % self.todict()

    def __iter__(self):
        return self.keys()

    def keys(self):
        return (event for event in self.events)

    def values(self):
        return (event._value for event in self.events)

    def items(self):
        return ((event, event._value) for event in self.events)

    def todict(self):
        return dict((event, event._value) for event in self.events)


class Condition(Event):
    """An event that gets triggered once the condition function *evaluate*
    returns ``True`` on the given list of *events*.

    The value of the condition event is an instance of :class:`ConditionValue`
    which allows convenient access to the input events and their values. The
    :class:`ConditionValue` will only contain entries for those events that
    occurred before the condition is processed.

    If one of the events fails, the condition also fails and forwards the
    exception of the failing event.

    The *evaluate* function receives the list of target events and the number
    of processed events in this list: ``evaluate(events, processed_count)``. If
    it returns ``True``, the condition is triggered. The
    :func:`Condition.all_events()` and :func:`Condition.any_events()` functions
    are used to implement *and* (``&``) and *or* (``|``) for events.

    Condition events can be nested.

    """
    def __init__(self, env, evaluate, events):
        super(Condition, self).__init__(env)
        self._evaluate = evaluate
        self._events = events if type(events) is tuple else tuple(events)
        self._count = 0

        if not self._events:
            # Immediately succeed if no events are provided.
            self.succeed(ConditionValue())
            return

        # Check if events belong to the same environment.
        for event in self._events:
            if self.env != event.env:
                raise ValueError('It is not allowed to mix events from '
                                 'different environments')

        # Check if the condition is met for each processed event. Attach
        # _check() as a callback otherwise.
        for event in self._events:
            if event.callbacks is None:
                self._check(event)
            else:
                event.callbacks.append(self._check)

        # Register a callback which will build the value of this condition
        # after it has been triggered.
        self.callbacks.append(self._build_value)

    def _desc(self):
        """Return a string *Condition(evaluate, [events])*."""
        return '%s(%s, %s)' % (self.__class__.__name__,
                               self._evaluate.__name__, self._events)

    def _populate_value(self, value):
        """Populate the *value* by recursively visiting all nested
        conditions."""

        for event in self._events:
            if isinstance(event, Condition):
                event._populate_value(value)
            elif event.callbacks is None:
                value.events.append(event)

    def _build_value(self, event):
        """Build the value of this condition."""
        if event.ok:
            self._value = ConditionValue()
            self._populate_value(self._value)

    def _check(self, event):
        """Check if the condition was already met and schedule the *event* if
        so."""
        if self._value is not PENDING:
            return

        self._count += 1

        if not event.ok:
            # Abort if the event has failed.
            event.defused = True
            self.fail(event._value)
        elif self._evaluate(self._events, self._count):
            # The condition has been met. The _collect_values callback will
            # populate set the value once this condition gets processed.
            self.succeed()

    @staticmethod
    def all_events(events, count):
        """An evaluation function that returns ``True`` if all *events* have
        been triggered."""
        return len(events) == count

    @staticmethod
    def any_events(events, count):
        """An evaluation function that returns ``True`` if at least one of
        *events* has been triggered."""
        return count > 0 or len(events) == 0


class AllOf(Condition):
    """A :class:`~simpy.events.Condition` event that is triggered if all of
    a list of *events* have been successfully triggered. Fails immediately if
    any of *events* failed.

    """
    def __init__(self, env, events):
        super(AllOf, self).__init__(env, Condition.all_events, events)


class AnyOf(Condition):
    """A :class:`~simpy.events.Condition` event that is triggered if any of
    a list of *events* has been successfully triggered. Fails immediately if
    any of *events* failed.

    """
    def __init__(self, env, events):
        super(AnyOf, self).__init__(env, Condition.any_events, events)


class Interrupt(Exception):
    """Exception thrown into a process if it is interrupted (see
    :func:`~simpy.events.Process.interrupt()`).

    :attr:`cause` provides the reason for the interrupt, if any.

    If a process is interrupted concurrently, all interrupts will be thrown
    into the process in the same order as they occurred.


    """
    def __str__(self):
        return '%s(%r)' % (self.__class__.__name__, self.cause)

    @property
    def cause(self):
        """The cause of the interrupt or ``None`` if no cause was provided."""
        return self.args[0]


def _describe_frame(frame):
    """Print filename, line number and function name of a stack frame."""
    filename, name = frame.f_code.co_filename, frame.f_code.co_name
    lineno = frame.f_lineno

    with open(filename) as f:
        for no, line in enumerate(f):
            if no + 1 == lineno:
                break

    return '  File "%s", line %d, in %s\n    %s\n' % (filename, lineno, name,
                                                      line.strip())
