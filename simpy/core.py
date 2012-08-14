from heapq import heappush, heappop
from itertools import count
from collections import defaultdict
from types import GeneratorType

from simpy.exceptions import Interrupt, Failure, SimEnd

Failed = 0
Success = 1
Init = 2
Infinity = float('inf')


class Process(object):
    __slots__ = ('id', 'pem', 'next_event', 'state', 'result', 'generator')
    def __init__(self, id, pem, generator):
        self.id = id
        self.pem = pem
        self.state = None
        self.next_event = None
        self.result = None
        self.generator = generator

    def __str__(self):
        if hasattr(self.pem, '__name__'):
            return self.pem.__name__
        else:
            return str(self.pem)

    def __repr__(self):
        if hasattr(self.pem, '__name__'):
            return self.pem.__name__
        else:
            return str(self.pem)


def process(ctx):
    return ctx.sim.active_proc


def now(ctx):
    return ctx.sim._now


def start(sim, pem, *args, **kwargs):
    process = pem(sim.context, *args, **kwargs)
    assert type(process) is GeneratorType, (
            'Process function %s is did not return a generator' % pem)
    proc = Process(next(sim.pid), pem, process)

    prev, sim.active_proc = sim.active_proc, proc
    # Schedule start of the process.
    sim._schedule(proc, Init, None)
    sim.active_proc = prev

    return proc


def exit(sim, result=None):
    sim.active_proc.result = result
    raise StopIteration()


def hold(sim, delta_t):
    assert delta_t >= 0
    proc = sim.active_proc
    assert proc.next_event is None

    sim._schedule(proc, Success, None, sim._now + delta_t)
    return Ignore


def resume(sim, other, value=None):
    if other.next_event is not None:
        assert other.next_event[0] != Init, (
                'Process %s is not initialized' % other)
    # TODO Isn't this dangerous? If other has already been resumed, this
    # call will silently drop the previous result.
    sim._schedule(other, Success, value)
    return Ignore


def interrupt(sim, other, cause=None):
    if other.next_event is not None:
        assert other.next_event[0] != Init, (
                'Process %s is not initialized' % other)
    proc = sim.active_proc
    sim._schedule(other, Failed, Interrupt(cause))


def signal(sim, other):
    """Interrupt this process, if the target terminates."""
    proc = sim.active_proc

    if other.generator is None:
        # FIXME This context switching is ugly.
        prev, sim.active_proc = sim.active_proc, other
        sim._schedule(proc, Failed, Interrupt(other))
        sim.active_proc = prev
    else:
        sim.signallers[other].append(proc)


Ignore = object()


class Simulation(object):
    context_funcs = (start, exit, interrupt, hold, resume, signal)
    context_props = (now, process)
    simulation_funcs = (start, interrupt, resume)

    def __init__(self):
        self.events = []
        self.joiners = defaultdict(list)
        self.signallers = defaultdict(list)

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
        proc.generator = None

        joiners = self.joiners.pop(proc, None)
        signallers = self.signallers.pop(proc, None)

        if proc.state == Failed:
            # TODO Don't know about this one. This check causes the whole
            # simulation to crash if there is a crashed process and no other
            # process to handle this crash. Something like this must certainely
            # be done, because exception should never ever be silently ignored.
            # Still, a check like this looks fishy to me.
            if not joiners and not signallers:
                raise proc.result.__cause__

        if joiners:
            for joiner in joiners:
                if joiner.generator is None: continue
                self._schedule(joiner, proc.state, proc.result)

        if signallers:
            for signaller in signallers:
                if signaller.generator is None: continue
                self._schedule(signaller, Failed, Interrupt(proc))

    def step(self):
        assert self.active_proc is None

        while True:
            try:
                self._now, eid, proc, evt = heappop(self.events)
            except IndexError:
                raise SimEnd()

            # Break from the loop if we find a valid event.
            if evt is proc.next_event:
                break

        evt_type, value = proc.next_event
        proc.next_event = None
        self.active_proc = proc
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

        if target is not None:
            if target is not Ignore:
                # TODO Improve this error message.
                assert type(target) is Process, 'Invalid yield value "%s"' % target
                # TODO The stacktrace won't show the position in the pem where this
                # exception occured. Maybe throw the assertion error into the pem?
                assert proc.next_event is None, 'Next event already scheduled!'

                # Add this process to the list of waiters.
                if target.generator is None:
                    # FIXME This context switching is ugly.
                    prev, self.active_proc = self.active_proc, target
                    # Process has already terminated. Resume as soon as possible.
                    self._schedule(proc, target.state, target.result)
                    self.active_proc = prev
                else:
                    self.joiners[target].append(proc)
            else:
                assert proc.next_event is not None
        else:
            assert proc.next_event is None, 'Next event already scheduled!'

        self.active_proc = None

    def peek(self):
        """
        Returns the time of the next event or ``inf`` if no more events are
        scheduled.

        """
        try:
            while True:
                # Pop all removed events from the queue
                # self.events[0][3] is the scheduled event
                # self.events[0][2] is the corresponding proc
                if self.events[0][3] is self.events[0][2].next_event:
                    break

                heappop(self.events)

            return self.events[0][0]  # time of first event
        except IndexError:
            return Infinity

    def step_dt(self, delta_t=1):
        """Executes all events that occur within the next *delta_t*
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

        try:
            while self.peek() < until:
                self.step()
        except SimEnd:
            pass
