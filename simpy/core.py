from heapq import heappush, heappop


class InterruptedException(Exception):
    def __init__(self, cause):
        Exception.__init__(self)
        self.cause = cause


class Failure(Exception):
    pass


class Context(object):
    # TODO Overwrite wait, join, signal, fork, interrupt and exit with a
    # failing function once the process has terminated?

    def __init__(self, sim, id, pem, args, kwargs):
        self.sim = sim
        self.id = id
        self.pem = pem
        self._next_event = None
        self._scheduled = True
        self.signallers = []
        self.joiners = []
        self.result = None

        self.process = pem(self, *args, **kwargs)

        # Schedule start of the process.
        self.sim.schedule(self, 0, Timeout, None)

    @property
    def now(self):
        return self.sim.now

    def wait(self, delay=None):
        assert not self._scheduled, ('Next event already scheduled! Did you'
            'forget to yield a call to Context.wait or Context.join?')
        self._scheduled = True

        if delay is None:
            # Wait indefinitely. Don't do anything.
            pass
        else:
            self.sim.schedule(self, delay, Timeout, None)

    def join(self, target):
        assert not self._scheduled, ('Next event already scheduled! Did you'
            'forget to yield a call to Context.wait or Context.join?')
        self._scheduled = True

        if target.process is None:
            # FIXME This context switching is ugly.
            prev, self.sim.active_ctx = self.sim.active_ctx, target
            # Process has already terminated. Resume as soon as possible.
            self.sim.schedule(self, 0,
                    Crash if type(target.result) is Failure else Join,
                    target.result)
            self.sim.active_ctx = prev
        else:
            target.joiners.append(self)

    def signal(self, target):
        """Interrupt this process, if the target terminates."""
        if target.process is None:
            # FIXME This context switching is ugly.
            prev, self.sim.active_ctx = self.sim.active_ctx, target
            self.sim.schedule(self, 0, Interrupt, InterruptedException(target))
            self.sim.active_ctx = prev
        else:
            target.signallers.append(self)

    def fork(self, pem, *args, **kwargs):
        return self.sim.create_context(pem, args, kwargs)

    def interrupt(self, cause=None):
        if self.process is None:
            raise RuntimeError('Process is dead')

        self.sim.schedule(self, 0, Interrupt, InterruptedException(cause))

    def exit(self, result=None):
        # TODO Check if this is the active context. This method must only be
        # called from within the process pem.
        self.result = result
        raise StopIteration()

    def __str__(self):
        return self.pem.__name__

Timeout = 1
Join = 2
Cancel = 0
Interrupt = -1
Crash = -2

class Simulation(object):
    def __init__(self, root, *args, **kwargs):
        self.events = []
        self.pid = 0
        self.now = 0
        self.active_ctx = None
        self.ctx = self.create_context(root, args, kwargs)

    def create_context(self, pem, args, kwargs):
        return Context(self, self._get_id(), pem, args, kwargs)

    def destroy_context(self, ctx):
        ctx.process = None

        if type(ctx.result) is Failure:
            # TODO Don't know about this one. This check causes the whole
            # simulation to crash if there is a crashed process and no other
            # process to handle this crash. Something like this must certainely
            # be done, because exception should never ever be silently ignored.
            # Still, a check like this looks fishy to me.
            if not ctx.joiners and not ctx.signallers:
                raise ctx.result.args[0]
            evt_type = Crash
        else:
            evt_type = Join

        for joiner in ctx.joiners:
            if joiner.process is None: continue
            self.schedule(joiner, 0, evt_type, ctx.result)

        for signaller in ctx.signallers:
            if signaller.process is None: continue
            self.schedule(signaller, 0, Interrupt, InterruptedException(ctx))

    def schedule(self, ctx, delay, evt_type, value):
        # Cancel the currently scheduled event if there is any.
        if ctx._next_event is not None:
            ctx._next_event[3] = Cancel

        # Schedule the event.
        evt = [self.now + delay, ctx.id, ctx, evt_type, value]
        heappush(self.events, evt)
        ctx._next_event = evt

    def _get_id(self):
        pid = self.pid
        self.pid += 1
        return pid

    def step(self):
        self.now, id, ctx, evt_type, value = heappop(self.events)
        if evt_type == Cancel:
            return

        ctx._next_event = None
        ctx._scheduled = False
        self.active_ctx = ctx
        try:
            if evt_type > 0:
                # A "successful" event, either Timeout or Join.
                ctx.process.send(value)
            else:
                # An "unsuccessful" event, either Interrupt or Crash.
                ctx.process.throw(value)
        except StopIteration:
            # Process has terminated.
            self.destroy_context(ctx)
        except BaseException as e:
            # Process has failed.
            ctx.result = Failure(e)
            self.destroy_context(ctx)

        self.active_ctx = None

    def peek(self):
        while self.events and self.events[0][3] == Cancel:
            heappop(self.events)
        return self.events[0][0]

    def simulate(self, until):
        while self.events and until > self.events[0][0]:
            self.step()
