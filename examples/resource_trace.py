from simpy.resource import Resource

def root(ctx, result=[]):
    resource = Resource(ctx, 'res')

    def child(ctx, name, resource, result):
        yield resource.request()
        result.append((name, ctx.now))
        yield ctx.wait(1)
        yield ctx.wait(1)
        resource.release()

    ctx.fork(child, 'a', resource, result)
    ctx.fork(child, 'b', resource, result)
    yield
