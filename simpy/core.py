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
            'joiners', 'subscribers', 'interrupts')

    def __init__(self, id, generator):
        self.id = id
        self.generator = generator
        self.name = self.generator.__name__
        self.state = None
        self.next_event = None
        self.result = None
        self.joiners = []
        self.subscribers = []
        self.interrupts = []

    def __repr__(self):
        return self.name


def process(ctx):
    return ctx.sim.active_proc


def now(ctx):
    return ctx.sim._now


def start(sim, pem, *args, **kwargs):
    process = pem(sim.context, *args, **kwargs)
    if type(process) is not GeneratorType:
        raise RuntimeError(
            'Process function %s is did not return a generator' % pem)
    proc = Process(next(sim.pid), process)

    prev, sim.active_proc = sim.active_proc, proc
    # Schedule start of the process.
    sim._schedule(proc, Init, None)
    sim.active_proc = prev

    return proc


def exit(sim, result=None):
    sim.active_proc.result = result
    raise StopIteration()


def wait(sim, delta_t):
    if delta_t < 0:
        raise RuntimeError('Invalid wait duration %.2f' % float(delta_t))

    proc = sim.active_proc
    if proc.next_event is not None:
        raise RuntimeError('Next event already scheduled')

    sim._schedule(proc, Success, None, sim._now + delta_t)
    return Ignore


def suspend(sim):
    proc = sim.active_proc
    if proc.next_event is not None:
        raise RuntimeError('Next event already scheduled')
    proc.next_event = (Suspended, None)
    return Ignore


def interrupt(sim, other, cause=None):
    if other.next_event[0] == Init:
        raise RuntimeError('Process %s is not initialized' % other)

    interrupts = other.interrupts
    if not interrupts:
        # This is the first interrupt, so schedule it.
        sim._schedule(other,
                Success if other.next_event[0] == Suspended else Failed,
                None)

    interrupts.append(cause)


def subscribe(sim, other):
    """Interrupt this process, if the target terminates."""
    proc = sim.active_proc

    if other.generator is None:
        # FIXME This context switching is ugly.
        prev, sim.active_proc = sim.active_proc, other
        proc.interrupts.append(other)
        sim.active_proc = prev
    else:
        other.subscribers.append(proc)


Ignore = object()


class Simulation(object):
    context_funcs = (start, exit, wait, suspend, interrupt, subscribe)
    context_props = (now, process)
    simulation_funcs = (start, interrupt)

    def __init__(self):
        self.events = []

        self.pid = count()
        self.eid = count()
        self.active_proc = None
        self._now = 0

        # Define context class for this simulation.
        class Context(object):
            pass

        # Attach properties to the context class.
        for prop in self.context_props:
            setattr(Context, prop.__name__, property(prop))

        # Instanciate the context and bind it to the simulation.
        self.context = Context()
        self.context.sim = self

        # Attach context function and bind them to the simulation.
        for func in self.context_funcs:
            setattr(self.context, func.__name__,
                    func.__get__(self, Simulation))

        # Attach public simulation functions to this instance.
        for func in self.simulation_funcs:
            setattr(self, func.__name__, func.__get__(self, Simulation))

    @property
    def now(self):
        return self._now

    def _schedule(self, proc, evt_type, value, at=None):
        if at is None:
            at = self._now

        proc.next_event = (evt_type, value)
        heappush(self.events, (at, next(self.eid), proc, proc.next_event))

    def _join(self, proc):
        joiners = proc.joiners
        subscribers = proc.subscribers
        interrupts = proc.interrupts

        proc.generator = None

        if proc.state == Failed:
            # TODO Don't know about this one. This check causes the whole
            # simulation to crash if there is a crashed process and no other
            # process to handle this crash. Something like this must certainely
            # be done, because exception should never ever be silently ignored.
            # Still, a check like this looks fishy to me.
            if not joiners and not subscribers:
                raise proc.result.__cause__

        if joiners:
            for joiner in joiners:
                if joiner.generator is None: continue
                self._schedule(joiner, proc.state, proc.result)

        if subscribers:
            for subscriber in subscribers:
                if subscriber.generator is None: continue
                self.context.interrupt(subscriber, proc)

    def peek(self):
        """Return the time of the next event or ``inf`` if no more
        events are scheduled.
        """

        while self.events:
            if self.events[0][2].next_event is self.events[0][3]: break
            heappop(self.events)
        return self.events[0][0] if self.events else Infinity

    def step(self):
        if self.active_proc is not None:
            raise RuntimeError('There is still an active process')

        while True:
            self._now, eid, proc, evt = heappop(self.events)

            # Break from the loop if we find a valid event.
            if evt is proc.next_event:
                break

        evt_type, value = evt
        proc.next_event = None
        self.active_proc = proc

        # Check if there are interrupts for this process.
        interrupts = proc.interrupts
        if interrupts:
            cause = interrupts.pop(0)
            value = cause if evt_type else Interrupt(cause)

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
            self._join(proc)
            self.active_proc = None
            return
        except BaseException as e:
            # Process has failed.
            proc.state = Failed
            proc.result = Failure()
            proc.result.__cause__ = e
            self._join(proc)
            self.active_proc = None
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
                prev, self.active_proc = self.active_proc, target
                # Process has already terminated. Resume as soon as possible.
                self._schedule(proc, target.state, target.result)
                self.active_proc = prev
            else:
                # FIXME This is a bit ugly. Because next_event cannot be
                # None this stub event is used. It will never be executed
                # because it isn't scheduled. This is necessary for
                # interrupt handling.
                proc.next_event = (Success, None)
                target.joiners.append(proc)

        # Schedule concurrent interrupts.
        if interrupts:
            self._schedule(proc,
                    Success if proc.next_event[0] == Suspended else Failed,
                    None)

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
