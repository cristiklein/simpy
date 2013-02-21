def root(ctx):
    def p1(ctx):
        yield ctx.wait(2)

    ctx.fork(p1)
    yield ctx.fork(p1)
    yield ctx.wait(1)
