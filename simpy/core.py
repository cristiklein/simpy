from heapq import heappush, heappop


class InterruptedException(Exception):
    pass


def interrupt(cause):
    def interrupt(process):
        process.throw(InterruptedException(cause))
    return interrupt


class Context(object):
    def __init__(self, sim, pem, args, kwargs):
        self.sim = sim
        self.id = self.sim._get_id()
        self.process = pem(self, *args, **kwargs)
        next(self.process)

    @property
    def now(self):
        return self.sim.now

    def wait(self, delta):
        heappush(self.sim.events, (self.sim.now + delta, self.id, self, next))

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
            pass

    def peek(self):
        return self.events[0][0]

    def simulate(self, until):
        while self.events and until > self.events[0][0]:
            self.step()
