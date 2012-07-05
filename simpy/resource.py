class Resource(object):
    def __init__(self, ctx, name, capacity=1):
        self.ctx = ctx
        self.name = name
        self.capacity = capacity
        self.waiters = []

    def request(self):
        if self.capacity > 0:
            self.capacity -= 1
            return self.ctx.resume(self.ctx.process)
        else:
            self.waiters.append(self.ctx.process)

    def release(self):
        self.capacity += 1
        while self.capacity > 0 and self.waiters:
            self.capacity -= 1
            self.ctx.resume(self.waiters.pop(0), None)
