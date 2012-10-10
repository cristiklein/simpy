import sys
from heapq import heappush, heappop
from itertools import count
from collections import defaultdict
from types import GeneratorType

Failed = -1
Interrupted = 0
Success = 1
Suspended = 2


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
    __slots__ = ('ctx', 'generator', 'event', 'joiners')

    def __init__(self, ctx, generator):
        self.ctx = ctx
        self.generator = generator
        self.joiners = []

    def __repr__(self):
        return self.generator.__name__

    @property
    def is_alive(self):
        return self.event is not None

    def interrupt(self, cause=None):
        if self.event is None:
            # Interrupts on dead process have no effect.
            return

        self.ctx._interrupt(self, cause)


class Context(object):
    def __init__(self, initial_time=0):
        self._now = initial_time
        self._events = []
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
        proc = Process(self, pem)

        # Schedule start of the process.
        self._schedule(proc, self._now, Success, None)
        return proc

    def exit(self, result=None):
        raise StopIteration(result)

    def wait(self, delta_t, value=None):
        if delta_t < 0:
            raise RuntimeError('Invalid wait duration %.2f' % float(delta_t))

        proc = self._active_proc
        if proc.event is not None:
            raise RuntimeError('Next event already scheduled')

        self._schedule(proc, self._now + delta_t, Success, value)
        return Ignore

    def suspend(self):
        proc = self._active_proc
        if proc.event is not None:
            raise RuntimeError('Next event already scheduled')
        proc.event = [None, None, self, Suspended, None]
        return Ignore

    def _schedule(self, proc, at, event, value):
        proc.event = [at, next(self._eid), proc, event, value]
        heappush(self._events, proc.event)

    def _interrupt(self, proc, value):
        # Cancel previous event.
        proc.event[2] = None
        interrupt = [self._now, next(self._eid), proc, Interrupted, value]
        heappush(self._events, interrupt)


Ignore = object()


def peek(ctx):
    """Return the time of the next event or ``inf`` if no more
    events are scheduled.
    """

    events = ctx._events
    while events:
        event = events[0]
        # Break from the loop if we find a valid event.
        if event[2] is not None:
            return event[0]
        heappop(events)
    return Infinity


def step(ctx):
    if ctx._active_proc is not None:
        raise RuntimeError('There is still an active process')

    while True:
        event = heappop(ctx._events)
        if event[2] is not None: break

    ctx._now, eid, proc, state, value = event

    if state is Interrupted:
        # FIXME Is this necessary? Consider the following situation for a
        # process:
        #  - 1: interrupt, 1: interrupt, 5: wait (cancelled)
        # The wait event will be skipped and the process will be called to
        # handle the interrupt, thereby scheduling another event. The queue
        # will now look like this:
        # - 1: interrupt, 1: wait
        # Note that wait isn't yet marked as cancelled and would be processed
        # if there weren't the call below:
        proc.event[2] = None
        # TODO If interrupts would always be scheduled with higher priority it
        # wouldn't even be necessary to cancel the event during
        # Context._interrupt. E.g: [<time>, <eid>, <etype>, <proc>, <value>]
        if proc.event[3] is Suspended:
            state = Suspended
        else:
            value = Interrupt(value)

    # Mark current event as processed.
    proc.event = None
    ctx._active_proc = proc

    try:
        target = (proc.generator.send(value) if state > 0 else
                proc.generator.throw(value))

        if target is not Ignore:
            # TODO Improve this error message.
            if type(target) is not Process:
                proc.generator.throw(RuntimeError('Invalid yield value "%s"' %
                        target))
            if proc.event is not None:
                proc.generator.throw(RuntimeError(
                        'Next event already scheduled'))

            # Add this process to the list of waiters.
            if proc not in target.joiners:
                if target.event is None:
                    proc.generator.throw(RuntimeError('Already terminated "%s"' %
                            target))
                else:
                    target.joiners.append(proc)

        ctx._active_proc = None
        return
    except StopIteration as e:
        # Process has terminated.
        evt_type = Success
        result = e.args[0] if e.args else None
    except BaseException as e:
        # Process has failed.
        evt_type = Failed
        result = Failure()
        result.__cause__ = e

        # The process has terminated, interrupt joiners.
        if not proc.joiners:
            # Crash the simulation if a process has crashed and no other
            # process is there to handle the crash.
            raise result.__cause__

    # Mark process as dead.
    proc.event = None

    for joiner in proc.joiners:
        if joiner.event is None: continue
        ctx._schedule(joiner, ctx._now, evt_type, result)

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
