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
import sys
from heapq import heappush, heappop
from inspect import isgenerator
from itertools import count


# Event priorities
INITIALIZE = 0
INTERRUPT = 1
CONTINUE = 2


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
    __slots__ = ('env', 'joiners',)

    def __init__(self, env):
        self.env = env
        self.joiners = []

    @property
    def is_alive(self):
        return self.joiners is not None

    # FIXME activate, resume and fail do not make sense for every event.
    # Processes and timeouts cannot be activated or anything. Maybe introduce a
    # BaseEvent class without these methods?
    def activate(self, event, evt_type, value):
        self.env._schedule(CONTINUE, self, evt_type, value)

    def resume(self, value=None):
        self.env._schedule(CONTINUE, self, True, value)

    def fail(self, value):
        self.env._schedule(CONTINUE, self, False, value)


class Timeout(Event):
    __slots__ = ('env', 'joiners',)

    def __init__(self, env, delay, value=None):
        if delay < 0:
            raise ValueError('Negative delay %f' % delay)

        self.env = env
        self.joiners = []

        env._schedule(CONTINUE, self, True, value, delay)
    
    def resume(self, value=None):
        raise RuntimeError('A timeout cannot be resumed')

    def fail(self, value=None):
        raise RuntimeError('A timeout cannot be failed')


class Process(Event):
    """A *Process* is a wrapper for instantiated PEMs.

    A Processes has a process event generator (``peg`` -- the generator
    that the PEM returns) and a reference to its :class:`Environment`
    ``env``. It also contains internal and external status information.
    It is also used for process interaction, e.g., for interruptions.

    An instance of this class is returned by
    :meth:`Environment.start()`.

    """
    __slots__ = ('env', 'generator', 'event', 'joiners',)

    def __init__(self, env, generator):
        if not isgenerator(generator):
            raise ValueError('%s is not a generator.' % generator)

        self.env = env
        self.generator = generator
        self.joiners = []
        self.event = None
        initialize = Event(env)
        initialize.joiners.append(self.process)
        env._schedule(INITIALIZE, initialize, True, None)

    def __repr__(self):
        """Returns the name of the :attr:`generator`."""
        return self.generator.__name__

    def interrupt(self, cause=None):
        if self.joiners is None:
            # Interrupts on dead process have no effect.
            return

        interrupt_evt = Event(self)
        interrupt_evt.joiners.append(self.process)
        self.env._schedule(INTERRUPT, interrupt_evt, False, Interrupt(cause))

    def process(self, event, evt_type, value):
        # Ignore dead processes. Multiple concurrently scheduled interrupts
        # cause this situation. If the process dies while handling the first
        # one, the remaining interrupts must be discarded.
        if self.joiners is None: return

        # If the current event (e.g. an interrupt) isn't the one the process
        # expects, remove it from the original events joiners list.
        if self.event is not None and self.event.joiners is not None:
            self.event.joiners.remove(self.process)
            self.event = None

        # Mark the current process as active.
        self.env._active_proc = self

        try:
            target = (self.generator.send(value) if evt_type else
                    self.generator.throw(value))

            try:
                if target.joiners is None:
                    # FIXME This is dangerous. If the process catches these
                    # exceptions it may yield another event, which will not get
                    # processed causing the process to become deadlocked.
                    self.generator.throw(RuntimeError('Already terminated "%s"' %
                            target))
                else:
                    # Add this process to the list of waiters.
                    target.joiners.append(self.process)
                    self.event = target
            except AttributeError:
                # FIXME Same problem as above.
                self.generator.throw(RuntimeError('Invalid yield value "%s"' %
                        target))

            self.env._active_proc = None
            return
        except StopIteration as e:
            # Process has terminated.
            evt_type = True
            result = e.args[0] if len(e.args) else None
        except BaseException as e:
            # The process has terminated, interrupt joiners.
            if not self.joiners:
                # Crash the simulation if a process has crashed and no other
                # process is there to handle the crash.
                raise e

            # Process has failed.
            evt_type = False
            # FIXME Isn't there a better way to obtain the exception type? For
            # example using (type, value, traceback) tuple?
            result = type(e)(*e.args)
            result.__cause__ = e

        # FIXME proc.joiners should ideally be set to None unconditionally, so
        # that it is impossible to become a joiner of this process after this
        # step. Currently that's still possible if there are joiners and not
        # consistent to the case of no joiners. There were some problems with
        # the immediate scheduling of the wait event. Examine!
        if self.joiners:
            self.env._schedule(CONTINUE, self, evt_type, result)
        else:
            self.joiners = None

        self.env._active_proc = None
    
    # FIXME Resume and fail do not make sense for a process. A process is
    # activated immediately. This methods should ideally be not there.
    def resume(self, value=None):
        raise RuntimeError('A process cannot be resumed')

    def fail(self, value=None):
        raise RuntimeError('A process cannot be failed')


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
    def process(self):
        """Property that returns the currently active process."""
        return self._active_proc

    @property
    def now(self):
        """Property that returns the current simulation time."""
        return self._now

    def start(self, peg):
        """Start a new process for ``peg``.

        *PEG* is the *Process Execution Generator*, which is the
        generator returned by *PEM*.

        """
        return Process(self, peg)

    def exit(self, result=None):
        raise StopIteration(result)

    def timeout(self, delta_t, value=None):
        return Timeout(self, delta_t, value)

    def suspend(self, name=''):
        return Event(self)

    def _schedule(self, priority, event, resume, value=None, delay=0):
        heappush(self._events, (self._now + delay, priority, next(self._eid),
                resume, event, value))


def peek(env):
    """Return the time of the next event or ``inf`` if no more
    events are scheduled.
    """
    return env._events[0][0] if env._events else Infinity


def step(env):
    env._now, _, _, resume, event, value = heappop(env._events)

    # Mark event as done.
    joiners, event.joiners = event.joiners, None

    for proc in joiners:
        proc(event, resume, value)


def simulate(env, until=Infinity):
    """Shortcut for ``while peek(env) < until: step(env)``.

    The parameter ``until`` specifies when the simulation ends. By
    default it is set to *infinity*, which means SimPy tries to simulate
    all events, which might take infinite time if your processes don't
    terminate on their own.

    """
    if until <= 0:
        raise ValueError('until(=%s) should be a number > 0.' % until)

    try:
        while env._events[0][0] < until:
            step(env)
    except IndexError:
        pass
