from simpy import Simulation, InterruptedException, Failure

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

        yield ctx.join(ctx.fork(pem))
        assert ctx.now == 10

    Simulation(root).simulate(until=20)

def test_process_result():
    def root(ctx):
        def pem(ctx):
            yield ctx.wait(10)
            ctx.exit('oh noes, i am dead x_x')
            assert False, 'Hey, i am alive? How is that possible?'

        result = yield ctx.join(ctx.fork(pem))
        assert result == 'oh noes, i am dead x_x'

    Simulation(root).simulate(until=20)

def test_wait_for_all():
    def root(ctx):
        def pem(ctx, i):
            yield ctx.wait(i)
            ctx.exit(i)

        # Fork many child processes and let them wait for a while. The first
        # child waits the longest time.
        processes = [ctx.fork(pem, i) for i in reversed(range(10))]

        # Wait until all children have been terminated.
        results = []
        for process in processes:
            results.append((yield ctx.join(process)))
        assert results == list(reversed(range(10)))

        # The first child should have terminated at timestep 9. Confirm!
        assert ctx.now == 9

    Simulation(root).simulate(until=20)

def test_wait_for_any():
    def root(ctx):
        def pem(ctx, i):
            yield ctx.wait(i)
            ctx.exit(i)

        # Fork many child processes and let them wait for a while. The first
        # child waits the longest time.
        processes = [ctx.fork(pem, i) for i in reversed(range(10))]

        def wait_for_any(ctx, processes):
            for process in processes:
                ctx.signal(process)
            try:
                yield ctx.wait()
                assert False, 'There should have been an interrupt'
            except InterruptedException as e:
                result = e.cause
            ctx.exit(result)

        # Wait until the a child has terminated.
        first_dead = yield ctx.join(ctx.fork(wait_for_any, processes))
        # Confirm that the child created at last has terminated as first.
        assert first_dead == processes[-1]
        assert first_dead.result == 0

    Simulation(root).simulate(until=20)

def test_crashing_process():
    def root(ctx):
        yield ctx.wait(1)
        raise RuntimeError("That's it, I'm done")

    try:
        Simulation(root).simulate(until=20)
        assert False, 'Fishy!! This is not supposed to happen!'
    except RuntimeError as exc:
        assert exc.args[0] == "That's it, I'm done"

def test_crashing_child_process():
    def root(ctx):
        def panic(ctx):
            yield ctx.wait(1)
            raise RuntimeError('Oh noes, roflcopter incoming... BOOM!')

        try:
            yield ctx.join(ctx.fork(panic))
            assert False, "Hey, where's the roflcopter?"
        except Failure as exc:
            cause = exc.args[0]
            assert type(cause) == RuntimeError
            assert cause.args[0] == 'Oh noes, roflcopter incoming... BOOM!'

    Simulation(root).simulate(until=20)
