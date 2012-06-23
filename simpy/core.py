from heapq import heappush, heappop
from itertools import count
from collections import defaultdict
from types import GeneratorType


class Interrupt(Exception):
    def __init__(self, cause):
        Exception.__init__(self)
        self.cause = cause


class Failure(Exception):
    pass


# TODO Create Context class somehow dynamically if context properties should
# also be supported.

Inactive = 0
Active = 1
Done = 2
Failed = 3


class Process(object):
    __slots__ = ('sim', 'id', 'pem', 'next_event', 'state', 'result',
            'process')
    def __init__(self, sim, id, pem, process):
        self.sim = sim
        self.id = id
        self.pem = pem
        self.next_event = None
        self.state = Inactive
        self.result = None
        self.process = process

    @property
    def now(self):
        return self.sim.now

    def __str__(self):
        return self.pem.__name__

    def __repr__(self):
        return self.pem.__name__


def context(func):
    func.context = True
    return func


class Context(object):
    def __init__(self, sim):
        self.sim = sim


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
        proc = Process(self, next(self.pid), pem, process)

        prev, self.active_proc = self.active_proc, proc
        # Schedule start of the process.
        self.schedule(proc, True, None)
        self.active_proc = prev

        return proc

    def join(self, proc):
        proc.process = None

        joiners = self.joiners.pop(proc, None)
        signallers = self.signallers.pop(proc, None)

        if proc.state == Failed:
            # TODO Don't know about this one. This check causes the whole
            # simulation to crash if there is a crashed process and no other
            # process to handle this crash. Something like this must certainely
            # be done, because exception should never ever be silently ignored.
            # Still, a check like this looks fishy to me.
            if not joiners and not signallers:
                raise proc.result.args[0]

        if joiners:
            for joiner in joiners:
                if joiner.process is None: continue
                self.schedule(joiner, proc.state == Done, proc.result)

        if signallers:
            for signaller in signallers:
                if signaller.process is None: continue
                self.schedule(signaller, False, Interrupt(proc))

    @context
    def exit(self, result=None):
        self.active_proc.result = result
        raise StopIteration()

    @context
    def resume(self, other, value=None):
        assert other.state == Active, 'Process %s is not active' % other
        # TODO Isn't this dangerous? If other has already been resumed, this
        # call will silently drop the previous result.
        self.schedule(other, True, value)

    @context
    def interrupt(self, other, cause=None):
        assert other.state == Active, 'Process %s is not active' % other
        proc = self.active_proc
        self.schedule(other, False, Interrupt(cause))

    @context
    def signal(self, other):
        """Interrupt this process, if the target terminates."""
        proc = self.active_proc

        if other.process is None:
            # FIXME This context switching is ugly.
            prev, self.active_proc = self.active_proc, other
            self.schedule(proc, False, Interrupt(other))
            self.active_proc = prev
        else:
            self.signallers[other].append(proc)

    def process(self, proc):
        assert self.active_proc is None

        evt_type, value = proc.next_event
        proc.next_event = None
        proc.state = Active
        self.active_proc = proc
        try:
            if evt_type:
                # A "successful" event.
                target = proc.process.send(value)
            else:
                # An "unsuccessful" event.
                target = proc.process.throw(value)
        except StopIteration:
            # Process has terminated.
            proc.state = Done
            self.join(proc)
            self.active_proc = None
            return
        except BaseException as e:
            # Process has failed.
            proc.state = Failed
            proc.result = Failure(e)
            self.join(proc)
            self.active_proc = None
            return

        if target is not None:
            # TODO Improve this error message.
            assert type(target) is Process, 'Invalid yield value "%s"' % target
            # TODO The stacktrace won't show the position in the pem where this
            # exception occured. Maybe throw the assertion error into the pem?
            assert proc.next_event is None, 'Next event already scheduled!'

            # Add this process to the list of waiters.
            if target.process is None:
                # FIXME This context switching is ugly.
                prev, self.active_proc = self.active_proc, target
                # Process has already terminated. Resume as soon as possible.
                self.schedule(proc, target.state == Done, target.result)
                self.active_proc = prev
            else:
                 self.joiners[target].append(proc)
        else:
            # FIXME This isn't working yet.
            #assert proc.next_event is None, 'Next event already scheduled!'
            pass

        self.active_proc = None


class SimulationContext(Context):
    @property
    def now(self):
        return self.sim.now


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
    def wait(self, delay=None):
        proc = self.active_proc
        assert proc.next_event is None

        if delay is None:
            # Mark this process as scheduled. This is to prevent multiple calls
            # to wait without a yield.
            proc.next_event = True
            return

        self.schedule(proc, True, None, self.now + delay)

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
