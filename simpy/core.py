import sys
from heapq import heappush, heappop
from itertools import count
from collections import defaultdict
from types import GeneratorType

Failed = 0
Success = 1
Init = 2
Suspended = 3


Infinity = float('inf')


class Interrupt(Exception):
    """This exceptions is sent into a process if it was interrupted by
    another process.

    """
    def __init__(self, cause):
        super(Interrupt, self).__init__(cause)

    @property
    def cause(self):
        return self.args[0]


class Failure(Exception):
    """This exception indicates that a process failed during its execution."""
    if sys.version_info < (3, 0):
        # Exception chaining was added in Python 3. Mimic exception chaining as
        # good as possible for Python 2.
        def __init__(self):
            super(Failure, self).__init__()
            self.stacktrace = traceback.format_exc(sys.exc_info()[2]).strip()

        def __str__(self):
            return 'Caused by the following exception:\n\n%s' % (
                    self.stacktrace)

    def __str__(self):
        return '%s' % self.__cause__


class Process(object):
    __slots__ = ('id', 'generator', 'name', 'next_event', 'state', 'result',
            'joiners', 'interrupts')

    def __init__(self, id, generator):
        self.id = id
        self.generator = generator
        self.name = self.generator.__name__
        self.state = None
        self.next_event = None
        self.result = None
        self.joiners = []
        self.interrupts = []

    def __repr__(self):
        return self.name

    @property
    def is_alive(self):
        return self.generator is not None


class Context(object):
    def __init__(self, initial_time=0):
        self._now = initial_time
        self._events = []
        self._pid = count()
        self._eid = count()
        self._active_proc = None

    @property
    def process(self):
        return self._active_proc

    @property
    def now(self):
        return self._now

    def start(self, pem):
        if type(pem) is not GeneratorType:
            raise RuntimeError(
                'Process function %s is not a generator' % pem)
        proc = Process(next(self._pid), pem)

        # Schedule start of the process.
        self._schedule(proc, Init, None, self._now)

        return proc

    def exit(self, result=None):
        self._active_proc.result = result
        raise StopIteration()

    def wait(self, delta_t, value=None):
        if delta_t < 0:
            raise RuntimeError('Invalid wait duration %.2f' % float(delta_t))

        proc = self._active_proc
        if proc.next_event is not None:
            raise RuntimeError('Next event already scheduled')

        self._schedule(proc, Success, value, self._now + delta_t)
        return Ignore

    def suspend(self):
        proc = self._active_proc
        if proc.next_event is not None:
            raise RuntimeError('Next event already scheduled')
        proc.next_event = (Suspended, None)
        return Ignore

    def interrupt(self, other, cause=None):
        if other.generator is None:
            # Interrupts on dead process have no effect.
            return

        interrupts = other.interrupts
        # Reschedule the current event, if this is the first interrupt.
        if not interrupts and other.next_event[0] != Init:
            # Keep the type of the next event in order to decide how the
            # interrupt should be send into the process.
            self._schedule(other, other.next_event[0], other.next_event[1],
                    self.now)

        interrupts.append(cause)

    def subscribe(self, other):
        """Interrupt this process, if the target terminates."""
        proc = self._active_proc

        if proc in other.joiners: return

        if other.generator is None:
            proc.interrupts.append(other)
        else:
            other.joiners.append(proc)

    def _schedule(self, proc, evt_type, value, at):
        proc.next_event = (evt_type, value)
        heappush(self._events, (at, next(self._eid), proc, proc.next_event))

    def _join(self, proc):
        joiners = proc.joiners
        interrupts = proc.interrupts

        proc.generator = None

        if proc.state == Failed:
            # TODO Don't know about this one. This check causes the whole
            # simulation to crash if there is a crashed process and no other
            # process to handle this crash. Something like this must certainely
            # be done, because exception should never ever be silently ignored.
            # Still, a check like this looks fishy to me.
            if not joiners:
                raise proc.result.__cause__

        for joiner in joiners:
            if joiner.generator is None: continue
            self.interrupt(joiner, proc)



Ignore = object()


def peek(ctx):
    """Return the time of the next event or ``inf`` if no more
    events are scheduled.
    """

    events = ctx._events
    while events:
        if events[0][2].next_event is events[0][3]: break
        heappop(events)
    return events[0][0] if events else Infinity


def step(ctx):
    if ctx._active_proc is not None:
        raise RuntimeError('There is still an active process')

    while True:
        ctx._now, eid, proc, evt = heappop(ctx._events)

        # Break from the loop if we find a valid event.
        if evt is proc.next_event:
            break

    evt_type, value = evt
    proc.next_event = None
    ctx._active_proc = proc

    # Check if there are interrupts for this process.
    interrupts = proc.interrupts
    if interrupts:
        cause = interrupts.pop(0)
        if evt_type == Suspended and (value is None or value is cause):
            # Only interrupts may trigger the continuation of a suspended
            # process. The cause of the interrupt is directly send (or
            # thrown in case of an exception) into the process.  Using an
            # Interrupt exception would be redundant.
            value = cause if value is None else cause.result
            evt_type = not isinstance(value, BaseException)
        else:
            # In all other cases an interrupt exception is thrown into the
            # process.
            value = Interrupt(cause)
            evt_type = Failed

    try:
        if evt_type:
            # A "successful" event.
            target = proc.generator.send(value)
        else:
            # An "unsuccessful" event.
            target = proc.generator.throw(value)
    except StopIteration:
        # Process has terminated.
        proc.state = Success
        ctx._join(proc)
        ctx._active_proc = None
        return
    except BaseException as e:
        # Process has failed.
        proc.state = Failed
        proc.result = Failure()
        proc.result.__cause__ = e
        ctx._join(proc)
        ctx._active_proc = None
        return

    if target is not Ignore:
        # TODO Improve this error message.
        if type(target) is not Process:
            proc.generator.throw(RuntimeError('Invalid yield value "%s"' %
                    target))
        if proc.next_event is not None:
            proc.generator.throw(RuntimeError(
                    'Next event already scheduled'))

        # Add this process to the list of waiters.
        if target.generator is None:
            # FIXME This context switching is ugly.
            prev, ctx._active_proc = ctx._active_proc, target
            # Process has already terminated. Resume as soon as possible.
            ctx._schedule(proc, target.state, target.result, ctx.now)
            ctx._active_proc = prev
        else:
            # FIXME This is a bit ugly. Because next_event cannot be
            # None this stub event is used. It will never be executed
            # because it isn't scheduled. This is necessary for
            # interrupt handling.
            proc.next_event = (Suspended, target)
            target.joiners.append(proc)

    # Schedule concurrent interrupts.
    if interrupts:
        ctx._schedule(proc, proc.next_event[0], proc.next_event[1],
                ctx.now)

    ctx._active_proc = None

def step_dt(ctx, delta_t=1):
    """Execute all events that occur within the next *delta_t*
    units of simulation time.

    """
    if delta_t <= 0:
        raise ValueError('delta_t(=%s) should be a number > 0.' % delta_t)

    until = ctx._now + delta_t
    while peek(ctx) < until:
        step(ctx)

def simulate(ctx, until=Infinity):
    """Shortcut for ``while sim.peek() < until: sim.step()``."""
    if until <= 0:
        raise ValueError('until(=%s) should be a number > 0.' % until)

    while peek(ctx) < until:
        step(ctx)
