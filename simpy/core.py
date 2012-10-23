import sys
from heapq import heappush, heappop
from itertools import count
from collections import defaultdict
from types import GeneratorType


Initialize = 0
Interrupted = 1
Resume = 2


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


class Event(object):
    __slots__ = ('ctx', 'joiners',)

    def __init__(self, ctx):
        self.ctx = ctx
        self.joiners = []

    @property
    def is_alive(self):
        return self.joiners is not None

    def resume(self, value=None):
        self.ctx._schedule(Resume, self, True, value)

    def fail(self, value):
        self.ctx._schedule(Resume, self, False, value)


class Wait(Event):
    __slots__ = ('ctx', 'joiners',)

    def __init__(self, ctx, delay, value=None):
        self.ctx = ctx
        self.joiners = []

        ctx._schedule(Resume, self, True, value, delay)
    
    def resume(self, value=None):
        raise RuntimeError('A timeout cannot be resumed')

    def fail(self, value=None):
        raise RuntimeError('A timeout cannot be failed')


class Process(Event):
    __slots__ = ('ctx', 'generator', 'event', 'joiners')

    def __init__(self, ctx, generator):
        self.ctx = ctx
        self.generator = generator
        self.joiners = []

        self.event = Event(ctx)
        self.event.joiners.append(self)
        ctx._schedule(Initialize, self.event, True, None)

    def __repr__(self):
        return self.generator.__name__

    def interrupt(self, cause=None):
        if self.joiners is None:
            # Interrupts on dead process have no effect.
            return

        interrupt_evt = Event(self)
        interrupt_evt.joiners.append(self)
        self.ctx._schedule(Interrupted, interrupt_evt, False, Interrupt(cause))


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
        return Process(self, pem)

    def exit(self, result=None):
        raise StopIteration(result)

    def wait(self, delta_t, value=None):
        return Wait(self, delta_t, value)

    def suspend(self, name=''):
        return Event(self)

    def _schedule(self, priority, event, resume, value=None, delay=0):
        heappush(self._events, (self._now + delay, priority, next(self._eid),
                resume, event, value))


def peek(ctx):
    """Return the time of the next event or ``inf`` if no more
    events are scheduled.
    """
    return ctx._events[0][0] if ctx._events else Infinity


def step(ctx):
    ctx._now, _, _, resume, event, value = heappop(ctx._events)

    process(ctx, resume, event, value)


def process(ctx, resume, event, value):
    if ctx._active_proc is not None:
        raise RuntimeError('There is still an active process')

    # Mark event as done.
    joiners, event.joiners = event.joiners, None

    for proc in joiners:
        # Ignore dead processes. Multiple concurrently scheduled interrupts
        # cause this situation. If the process dies while handling the first
        # one, the remaining interrupts must be discarded.
        if proc.joiners is None: continue

        # If the current event (e.g. an interrupt) isn't the one the process
        # expects, remove it from the original events joiners list.
        if event is not proc.event and proc.event is not None:
            proc.event.joiners.remove(proc)
            proc.event = None

        # Mark the current process as active.
        ctx._active_proc = proc

        try:
            target = (proc.generator.send(value) if resume else
                    proc.generator.throw(value))

            try:
                if target.joiners is None:
                    # FIXME This is dangerous. If the process catches these
                    # exceptions it may yield another event, which will not get
                    # processed causing the process to become deadlocked.
                    proc.generator.throw(RuntimeError('Already terminated "%s"' %
                            target))
                else:
                    # Add this process to the list of waiters.
                    target.joiners.append(proc)
                    proc.event = target
            except AttributeError:
                # FIXME Same problem as above.
                proc.generator.throw(RuntimeError('Invalid yield value "%s"' %
                        target))

            continue
        except StopIteration as e:
            # Process has terminated.
            evt_type = True
            result = e.args[0] if len(e.args) else None
        except BaseException as e:
            # Process has failed.
            evt_type = False
            # FIXME Isn't there a better way to obtain the exception type? For
            # example using (type, value, traceback) tuple?
            result = type(e)(*e.args)
            result.__cause__ = e

            # The process has terminated, interrupt joiners.
            if not proc.joiners:
                # Crash the simulation if a process has crashed and no other
                # process is there to handle the crash.
                raise result

        # FIXME proc.joiners should ideally be set to None unconditionally, so
        # that it is impossible to become a joiner of this process after this
        # step. Currently that's still possible if there are joiners and not
        # consistent to the case of no joiners. There were some problems with
        # the immediate scheduling of the wait event. Examine!
        if proc.joiners:
            ctx._schedule(Resume, proc, evt_type, result)
        else:
            proc.joiners = None

    ctx._active_proc = None


def simulate(ctx, until=Infinity):
    """Shortcut for ``while sim.peek() < until: sim.step()``."""
    if until <= 0:
        raise ValueError('until(=%s) should be a number > 0.' % until)

    try:
        while ctx._events[0][0] < until:
            step(ctx)
    except IndexError:
        pass
