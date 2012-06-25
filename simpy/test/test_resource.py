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


def test_resource_capacity():
    def root(ctx, result):
        resource = Resource(ctx, 'res', capacity=3)

        def child(ctx, name, resource, result):
            yield resource.request()
            result.append((name, ctx.now))
            yield ctx.wait(1)
            resource.release()

        for id in range(9):
            ctx.fork(child, '%d' % id, resource, result)
        yield

    result = []
    simulate(4, root, result)

    assert result == [('0', 0), ('1', 0), ('2', 0),
            ('3', 1), ('4', 1), ('5', 1),
            ('6', 2), ('7', 2), ('8', 2),
    ]
