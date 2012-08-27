from simpy.resource import Resource


def test_resource(sim, log):
    def root(ctx, log):
        resource = Resource(ctx, 'res')

        def child(ctx, name, resource, log):
            yield resource.request()
            log.append((name, ctx.now))
            yield ctx.wait(1)
            resource.release()

        ctx.start(child, 'a', resource, log)
        ctx.start(child, 'b', resource, log)
        yield ctx.suspend()

    sim.start(root, log)
    sim.simulate(4)

    assert log == [('a', 0), ('b', 1)]


def test_resource_capacity(sim, log):
    def root(ctx, log):
        resource = Resource(ctx, 'res', capacity=3)

        def child(ctx, name, resource, log):
            yield resource.request()
            log.append((name, ctx.now))
            yield ctx.wait(1)
            resource.release()

        for id in range(9):
            ctx.start(child, '%d' % id, resource, log)
        yield ctx.suspend()

    sim.start(root, log)
    sim.simulate(4)

    assert log == [('0', 0), ('1', 0), ('2', 0),
            ('3', 1), ('4', 1), ('5', 1),
            ('6', 2), ('7', 2), ('8', 2),
    ]
