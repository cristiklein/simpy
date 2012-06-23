class Resource(object):
    def __init__(self, ctx, name, capacity=1):
        self.ctx = ctx
        self.name = name
        self.capacity = capacity
        self.waiters = []

    def waiter(self, ctx):
        yield ctx.suspend()

    def check(self, ctx):
        self.resume()
        yield

    def resume(self, ctx=None):
        while self.capacity > 0 and self.waiters:
            self.capacity -= 1
            self.ctx.resume(self.waiters.pop(0), None)

    def request(self):
        waiter = self.ctx.fork(self.waiter)
        self.waiters.append(waiter)
        self.ctx.fork(self.check)
        return waiter

    def release(self):
        self.capacity += 1
        self.resume()
