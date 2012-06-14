from simpy import Simulation, InterruptedException

def test_simple_process():
    def pem(ctx, result):
        while True:
            result.append(ctx.now)
            yield ctx.wait(1)

    result = []
    Simulation(pem, result).simulate(until=4)

    assert result == [0, 1, 2, 3]

def test_interrupt():
    def root(ctx):
        def pem(ctx):
            try:
                yield ctx.wait(10)
                raise RuntimeError('Expected an interrupt')
            except InterruptedException:
                pass

        process = ctx.fork(pem)
        yield ctx.wait(5)
        process.interrupt()

    Simulation(root).simulate(until=20)

def test_wait_for_process():
    def root(ctx):
        def pem(ctx):
            yield ctx.wait(10)

        yield ctx.wait(ctx.fork(pem))
        assert ctx.now == 10

    Simulation(root).simulate(until=20)

def test_process_result():
    def root(ctx):
        def pem(ctx):
            yield ctx.wait(10)
            ctx.exit('oh noes, i am dead x_x')

        result = yield ctx.wait(ctx.fork(pem))
        assert result == 'oh noes, i am dead x_x'

    Simulation(root).simulate(until=20)
