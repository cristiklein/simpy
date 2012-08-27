class Resource(object):
    def __init__(self, ctx, name, capacity=1):
        self.ctx = ctx
        self.name = name
        self.capacity = capacity
        self.waiters = []

    def request(self):
        if self.capacity > 0:
            self.capacity -= 1
            return self.ctx.wait(0)
        else:
            self.waiters.append(self.ctx.process)
            return self.ctx.suspend()

    def release(self):
        if self.waiters:
            self.ctx.interrupt(self.waiters.pop(0))
        else:
            self.capacity += 1
