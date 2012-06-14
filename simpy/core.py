from heapq import heappush, heappop


class InterruptedException(Exception):
    pass


class Failure(Exception):
    pass


def interrupt(cause):
    def interrupt(process):
        process.throw(InterruptedException(cause))
    return interrupt


def resume(value=None):
    def resume(process):
        if type(value) is Failure:
            process.throw(value)
        else:
            process.send(value)
    return resume


class Context(object):
    def __init__(self, sim, pem, args, kwargs):
        self.sim = sim
        self.id = self.sim._get_id()
        self.process = pem(self, *args, **kwargs)
        self.waiters = []
        self.result = None
        next(self.process)

    @property
    def now(self):
        return self.sim.now

    def wait(self, until=None, value=None):
        # TODO This method is getting ugly. Maybe introduce separate functions
        # for each case?
        if self.process is None:
            # TODO Should we raise an exception in this case. This happens for
            # example if this process has registered to wake on the termination
            # of another process, but has already terminated in the meanwhile.
            return

        if type(until) is Context:
            if until.process is None:
                # Process has already terminated. Resume as soon as possible.
                heappush(self.sim.events, (self.sim.now, self.id, self,
                    resume(until.result)))
            else:
                until.waiters.append(self)
        elif until is None:
            # Wait indefinitely. Don't do anything.
            pass
        elif value is None:
            heappush(self.sim.events, (self.sim.now + until, self.id, self,
                next))
        else:
            heappush(self.sim.events, (self.sim.now + until, self.id, self,
                resume(value)))

    def wake(self, target):
        """Interrupt this process, if the target terminates."""
        target.waiters.append(self)

    def fork(self, pem, *args, **kwargs):
        return Context(self.sim, pem, args, kwargs)

    def interrupt(self, cause=None):
        # Cancel the currently scheduled event.
        for idx in range(len(self.sim.events)):
            if self.sim.events[idx][1] == self.id:
                self.sim.events[idx] = (-1, self.id, self, None)
                break

        # Schedule interrupt.
        heappush(self.sim.events, (self.sim.now, self.id, self,
                interrupt(cause)))

    def exit(self, result=None):
        # TODO Check if this is the active context. This method must only be
        # called from within the process pem.
        self.result = result
        raise StopIteration()


class Simulation(object):
    def __init__(self, root, *args, **kwargs):
        self.events = []
        self.pid = 0
        self.now = 0
        self.ctx = Context(self, root, args, kwargs)

    def _get_id(self):
        pid = self.pid
        self.pid += 1
        return pid

    def step(self):
        while True:
            self.now, id, ctx, func = heappop(self.events)
            if self.now >= 0: break

        try:
            func(ctx.process)
        except StopIteration:
            # Process has terminated.
            ctx.process = None

            # Resume processes waiting on the current one.
            for waiter in ctx.waiters:
                waiter.wait(0, ctx.result)
        except BaseException as e:
            ctx.result = Failure(e)

            # TODO Don't know about this one. This check causes the whole
            # simulation to crash if there is a crashed process and no other
            # process to handle this crash. Something like this must certainely
            # be done, because exception should never ever be silently ignored.
            # Still, a check like this looks fishy to me.
            if not ctx.waiters:
                raise

            for waiter in ctx.waiters:
                waiter.wait(0, ctx.result)


    def peek(self):
        return self.events[0][0]

    def simulate(self, until):
        while self.events and until > self.events[0][0]:
            self.step()
