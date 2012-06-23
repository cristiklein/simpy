import inspect
from heapq import heappush, heappop
from itertools import count
from collections import defaultdict


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


class Context(object):
    def __init__(self, sim, id, pem, args, kwargs):
        self.sim = sim
        self.id = id
        self.pem = pem
        self.next_event = None
        self.state = Inactive
        self.result = None

        for func in sim.context_funcs:
            setattr(self, func.__name__, func)

        self.process = pem(self, *args, **kwargs)

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


class Dispatcher(object):
    def __init__(self):
        self.events = []
        self.joiners = defaultdict(list)
        self.signallers = defaultdict(list)
        self.pid = count()
        self.active_ctx = None

        self.context_funcs = []
        for name in dir(self):
            obj = getattr(self, name)
            if callable(obj) and hasattr(obj, 'context'):
                self.context_funcs.append(obj)

    def schedule(self, ctx, evt_type, value):
        ctx.next_event = (evt_type, value)
        self.events.append((ctx, ctx.next_event))

    @context
    def fork(self, pem, *args, **kwargs):
        assert inspect.isgeneratorfunction(pem), (
                'Process function %s is not a generator' % pem)
        ctx = Context(self, next(self.pid), pem, args, kwargs)

        prev, self.active_ctx = self.active_ctx, ctx
        # Schedule start of the process.
        self.schedule(ctx, True, None)
        self.active_ctx = prev

        return ctx

    def join(self, ctx):
        ctx.process = None

        joiners = self.joiners.pop(ctx, None)
        signallers = self.signallers.pop(ctx, None)

        if ctx.state == Failed:
            # TODO Don't know about this one. This check causes the whole
            # simulation to crash if there is a crashed process and no other
            # process to handle this crash. Something like this must certainely
            # be done, because exception should never ever be silently ignored.
            # Still, a check like this looks fishy to me.
            if not joiners and not signallers:
                raise ctx.result.args[0]

        if joiners:
            for joiner in joiners:
                if joiner.process is None: continue
                self.schedule(joiner, ctx.state == Done, ctx.result)

        if signallers:
            for signaller in signallers:
                if signaller.process is None: continue
                self.schedule(signaller, False, Interrupt(ctx))

    @context
    def exit(self, result=None):
        self.active_ctx.result = result
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
        ctx = self.active_ctx
        self.schedule(other, False, Interrupt(cause))

    @context
    def signal(self, other):
        """Interrupt this process, if the target terminates."""
        ctx = self.active_ctx

        if other.process is None:
            # FIXME This context switching is ugly.
            prev, self.active_ctx = self.active_ctx, other
            self.schedule(ctx, False, Interrupt(other))
            self.active_ctx = prev
        else:
            self.signallers[other].append(ctx)

    def process(self, ctx):
        assert self.active_ctx is None

        evt_type, value = ctx.next_event
        ctx.next_event = None
        ctx.state = Active
        self.active_ctx = ctx
        try:
            if evt_type:
                # A "successful" event.
                target = ctx.process.send(value)
            else:
                # An "unsuccessful" event.
                target = ctx.process.throw(value)
        except StopIteration:
            # Process has terminated.
            ctx.state = Done
            self.join(ctx)
            self.active_ctx = None
            return
        except BaseException as e:
            # Process has failed.
            ctx.state = Failed
            ctx.result = Failure(e)
            self.join(ctx)
            self.active_ctx = None
            return

        if target is not None:
            # TODO Improve this error message.
            assert type(target) is Context, 'Invalid yield value "%s"' % target
            # TODO The stacktrace won't show the position in the pem where this
            # exception occured. Maybe throw the assertion error into the pem?
            assert ctx.next_event is None, 'Next event already scheduled!'

            # Add this process to the list of waiters.
            if target.process is None:
                # FIXME This context switching is ugly.
                prev, self.active_ctx = self.active_ctx, target
                # Process has already terminated. Resume as soon as possible.
                self.schedule(ctx, target.state == Done, target.result)
                self.active_ctx = prev
            else:
                 self.joiners[target].append(ctx)
        else:
            # FIXME This isn't working yet.
            #assert ctx.next_event is None, 'Next event already scheduled!'
            pass

        self.active_ctx = None


class Simulation(Dispatcher):
    def __init__(self):
        Dispatcher.__init__(self)
        self.now = 0
        self.eid = count()

    def schedule(self, ctx, evt_type, value, at=None):
        if at is None:
            at = self.now

        ctx.next_event = (evt_type, value)
        heappush(self.events, (at, next(self.eid), ctx, ctx.next_event))

    @context
    def wait(self, delay=None):
        ctx = self.active_ctx
        assert ctx.next_event is None

        if delay is None:
            # Mark this context as scheduled. This is to prevent multiple calls
            # to wait without a yield.
            ctx.next_event = True
            return

        # Next event wird von process gebraucht, um das Ergebnis reinzusenden.
        self.schedule(ctx, True, None, self.now + delay)

    def step(self):
        self.now, eid, ctx, evt = heappop(self.events)
        if ctx.next_event is not evt: return
        self.process(ctx)

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
    ctx = sim.fork(root, *args, **kwargs)
    return sim.simulate(until)
