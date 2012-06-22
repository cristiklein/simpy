from heapq import heappush, heappop
from itertools import count


class InterruptedException(Exception):
    def __init__(self, cause):
        Exception.__init__(self)
        self.cause = cause


class Failure(Exception):
    pass


# TODO Create Context class somehow dynamically if context properties should
# also be supported.

class Context(object):
    def __init__(self, sim, id, pem, args, kwargs):
        self.sim = sim
        self.id = id
        self.pem = pem
        self.next_event = None
        self.signallers = []
        self.joiners = []
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
        # TODO Handle immediately terminating processes (e.g. no generators).
        ctx = Context(self, next(self.pid), pem, args, kwargs)

        prev, self.active_ctx = self.active_ctx, ctx
        # Schedule start of the process.
        self.schedule(ctx, True, None)
        self.active_ctx = prev

        return ctx

    def join(self, ctx):
        ctx.process = None

        if not ctx.result_type:
            # TODO Don't know about this one. This check causes the whole
            # simulation to crash if there is a crashed process and no other
            # process to handle this crash. Something like this must certainely
            # be done, because exception should never ever be silently ignored.
            # Still, a check like this looks fishy to me.
            if not ctx.joiners and not ctx.signallers:
                raise ctx.result.args[0]

        for joiner in ctx.joiners:
            if joiner.process is None: continue
            self.schedule(joiner, ctx.result_type, ctx.result)

        for signaller in ctx.signallers:
            if signaller.process is None: continue
            self.schedule(signaller, False, InterruptedException(ctx))

    @context
    def exit(self, result=None):
        self.active_ctx.result = result
        raise StopIteration()

    @context
    def suspend(self):
        ctx = self.active_ctx
        assert ctx.next_event is None, 'Next event already scheduled!'
        ctx.next_event = True

    @context
    def resume(self, other, value=None):
        # TODO Isn't this dangerous? If other has already been resumed, this
        # call will silently drop the previous result.
        self.schedule(other, True, value)

    @context
    def interrupt(self, other, cause=None):
        ctx = self.active_ctx
        self.schedule(other, False, InterruptedException(cause))

    @context
    def signal(self, other):
        """Interrupt this process, if the target terminates."""
        ctx = self.active_ctx

        if other.process is None:
            # FIXME This context switching is ugly.
            prev, self.active_ctx = self.active_ctx, other
            self.schedule(ctx, False, InterruptedException(other))
            self.active_ctx = prev
        else:
            other.signallers.append(ctx)

    def process(self, ctx):
        assert self.active_ctx is None

        evt_type, value = ctx.next_event
        ctx.next_event = None
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
            ctx.result_type = True
            self.join(ctx)
            self.active_ctx = None
            return
        except BaseException as e:
            # Process has failed.
            ctx.result_type = False
            ctx.result = Failure(e)
            self.join(ctx)
            self.active_ctx = None
            return

        if target is not None:
            # TODO The stacktrace won't show the position in the pem where this
            # exception occured. Maybe throw the assertion error into the pem?
            assert ctx.next_event is None, 'Next event already scheduled!'

            # Add this process to the list of waiters.
            if target.process is None:
                # FIXME This context switching is ugly.
                prev, self.active_ctx = self.active_ctx, target
                # Process has already terminated. Resume as soon as possible.
                self.schedule(ctx, target.result_type, target.result)
                self.active_ctx = prev
            else:
                target.joiners.append(self.active_ctx)

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
            return self.suspend()

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
