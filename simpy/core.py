from __future__ import print_function

import sys

if sys.version_info < (2, 6):
    print('Only Python version 2.6 and above are supported')
    sys.exit(1)

from heapq import heappush, heappop
from itertools import count
from collections import defaultdict
from types import GeneratorType
import traceback


class Interrupt(Exception):
    def __init__(self, cause):
        Exception.__init__(self, cause)

    @property
    def cause(self):
        return self.args[0]


class Failure(Exception):
    if sys.version_info < (3, 0):
        # Exception chaining was added in Python 3. Mimic exception chaining as
        # good as possible for Python 2.
        def __init__(self):
            Exception.__init__(self)
            self.stacktrace = traceback.format_exc(sys.exc_info()[2]).strip()

        def __str__(self):
            return 'Caused by the following exception:\n\n%s' % (
                    self.stacktrace)


Failed = 0
Success = 1
Init = 2


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


def context(func):
    func.context = True
    return func


class Context(object):
    def __init__(self, sim):
        self.sim = sim

    @property
    def process(self):
        return self.sim.active_proc


Ignore = object()


class Dispatcher(object):
    def __init__(self, context_type):
        self.context_type = context_type
        self.events = []
        self.joiners = defaultdict(list)
        self.signallers = defaultdict(list)
        self.pid = count()
        self.active_proc = None

        self.context_funcs = {}
        for name in dir(self):
            obj = getattr(self, name)
            if callable(obj) and hasattr(obj, 'context'):
                self.context_funcs[name] = obj

        self.context = context_type(self)
        for name, func in self.context_funcs.items():
            setattr(self.context, name, func)

    def schedule(self, proc, evt_type, value):
        proc.next_event = (evt_type, value)
        self.events.append((proc, proc.next_event))

    @context
    def fork(self, pem, *args, **kwargs):
        process = pem(self.context, *args, **kwargs)
        assert type(process) is GeneratorType, (
                'Process function %s is did not return a generator' % pem)
        proc = Process(next(self.pid), pem, process)

        prev, self.active_proc = self.active_proc, proc
        # Schedule start of the process.
        self.schedule(proc, Init, None)
        self.active_proc = prev

        return proc

    def join(self, proc):
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
                self.schedule(joiner, proc.state, proc.result)

        if signallers:
            for signaller in signallers:
                if signaller.generator is None: continue
                self.schedule(signaller, Failed, Interrupt(proc))

    @context
    def exit(self, result=None):
        self.active_proc.result = result
        raise StopIteration()

    @context
    def resume(self, other, value=None):
        if other.next_event is not None:
            assert other.next_event[0] != Init, (
                    'Process %s is not initialized' % other)
        # TODO Isn't this dangerous? If other has already been resumed, this
        # call will silently drop the previous result.
        self.schedule(other, Success, value)
        return Ignore

    @context
    def interrupt(self, other, cause=None):
        if other.next_event is not None:
            assert other.next_event[0] != Init, (
                    'Process %s is not initialized' % other)
        proc = self.active_proc
        self.schedule(other, Failed, Interrupt(cause))

    @context
    def signal(self, other):
        """Interrupt this process, if the target terminates."""
        proc = self.active_proc

        if other.generator is None:
            # FIXME This context switching is ugly.
            prev, self.active_proc = self.active_proc, other
            self.schedule(proc, Failed, Interrupt(other))
            self.active_proc = prev
        else:
            self.signallers[other].append(proc)

    def process(self, proc):
        assert self.active_proc is None

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
            self.join(proc)
            self.active_proc = None
            return
        except BaseException as e:
            # Process has failed.
            proc.state = Failed
            proc.result = Failure()
            proc.result.__cause__ = e
            self.join(proc)
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
                    self.schedule(proc, target.state, target.result)
                    self.active_proc = prev
                else:
                    self.joiners[target].append(proc)
            else:
                assert proc.next_event is not None
        else:
            assert proc.next_event is None, 'Next event already scheduled!'

        self.active_proc = None


class SimulationContext(Context):
    @property
    def now(self):
        return self.sim.now


def wait(ctx):
    yield ctx.exit()


class Simulation(Dispatcher):
    def __init__(self):
        Dispatcher.__init__(self, SimulationContext)
        self.now = 0
        self.eid = count()

    def schedule(self, proc, evt_type, value, at=None):
        if at is None:
            at = self.now

        proc.next_event = (evt_type, value)
        heappush(self.events, (at, next(self.eid), proc, proc.next_event))

    @context
    def wait(self, delay):
        assert delay >= 0
        proc = self.active_proc
        assert proc.next_event is None

        self.schedule(proc, Success, None, self.now + delay)
        return Ignore

    def step(self):
        self.now, eid, proc, evt = heappop(self.events)
        if proc.next_event is not evt: return
        self.process(proc)

    def peek(self):
        while self.events:
            if self.events[0][2].next_event is self.events[0][3]: break
            heappop(self.events)
        return self.events[0][0]

    def simulate(self, until):
        while self.events and until > self.events[0][0]:
            self.step()


def simulate(until, root, *args, **kwargs):
    sim = Simulation()
    proc = sim.fork(root, *args, **kwargs)
    return sim.simulate(until)
