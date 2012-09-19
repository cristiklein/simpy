from simpy.resource import Resource


def test_resource(ctx):
    resource = Resource(ctx, 'res')

    def child(ctx, name, resource, log):
        yield resource.request()
        log.append((name, ctx.now))
        yield ctx.wait(1)
        resource.release()

    log = []
    a = ctx.start(child(ctx, 'a', resource, log))
    b = ctx.start(child(ctx, 'b', resource, log))
    yield a
    yield b

    assert log == [('a', 0), ('b', 1)]


def test_resource_capacity(ctx):
    resource = Resource(ctx, 'res', capacity=3)

    def child(ctx, name, resource, log):
        yield resource.request()
        log.append((name, ctx.now))
        yield ctx.wait(1)
        resource.release()

    log = []
    children = [ctx.start(child(ctx, '%d' % id, resource, log))
            for id in range(9)]

    for child in children:
        yield child

    assert log == [('0', 0), ('1', 0), ('2', 0),
            ('3', 1), ('4', 1), ('5', 1),
            ('6', 2), ('7', 2), ('8', 2),
    ]
