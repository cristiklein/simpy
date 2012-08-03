from heapq import heappush, heappop

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
        heappush(self.sim.events, (self.sim.now + delta, self.id, self))

    def fork(self, pem, *args, **kwargs):
        return Context(self.sim, pem, args, kwargs)


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
        self.now, id, ctx = heappop(self.events)
        try:
            next(ctx.process)
        except StopIteration:
            pass

    def peek(self):
        return self.events[0][0]

    def simulate(self, until):
        while self.events and until > self.events[0][0]:
            self.step()
