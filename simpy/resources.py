class Resource(object):
    def __init__(self, ctx, name, capacity=1):
        self.ctx = ctx
        self.name = name
        self.capacity = capacity
        self.waiters = []

    def request(self):
        if self.capacity > 0:
            self.capacity -= 1
            return self.ctx.resume(self.ctx.active_process)
        else:
            self.waiters.append(self.ctx.active_process)

    def release(self):
        if self.waiters:
            self.ctx.resume(self.waiters.pop(0), None)
        else:
            self.capacity += 1
