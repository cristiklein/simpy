class Resource(object):
    def __init__(self, ctx, name, capacity=1):
        self.ctx = ctx
        self.name = name
        self.capacity = capacity
        self.waiters = []

    def waiter(self, ctx):
        if self.capacity > 0:
            self.capacity -= 1
            ctx.exit()

        self.waiters.append(ctx.process)
        yield

    def resume(self, ctx=None):
        while self.capacity > 0 and self.waiters:
            self.capacity -= 1
            self.ctx.resume(self.waiters.pop(0), None)

    def request(self):
        return self.ctx.fork(self.waiter)

    def release(self):
        self.capacity += 1
        self.resume()
