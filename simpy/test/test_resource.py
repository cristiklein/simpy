from simpy import simulate
from simpy.resource import Resource

def test_resource():
    def root(ctx, result):
        resource = Resource(ctx, 'res')

        def child(ctx, name, resource, result):
            yield resource.request()
            result.append((name, ctx.now))
            yield ctx.wait(1)
            resource.release()

        ctx.fork(child, 'a', resource, result)
        ctx.fork(child, 'b', resource, result)
        yield

    result = []
    simulate(4, root, result)

    assert result == [('a', 0), ('b', 1)]
