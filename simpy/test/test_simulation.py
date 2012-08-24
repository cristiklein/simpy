from simpy import Interrupt, Failure


pytest_plugins = ['simpy.test.support']


def test_join(sim):
    def root(ctx):
        def pem(ctx):
            yield ctx.hold(10)

        yield ctx.start(pem)
        assert ctx.now == 10

    sim.start(root)
    sim.simulate(20)


def test_join_log(sim):
    def root(ctx):
        def pem(ctx):
            yield ctx.hold(10)
            ctx.exit('oh noes, i am dead x_x')
            assert False, 'Hey, i am alive? How is that possible?'

        log = yield ctx.start(pem)
        assert log == 'oh noes, i am dead x_x'

    sim.start(root)
    sim.simulate(20)


def test_join_after_terminate(sim):
    def root(ctx):
        def pem(ctx):
            yield ctx.hold(10)
            ctx.exit('oh noes, i am dead x_x')
            assert False, 'Hey, i am alive? How is that possible?'

        child = ctx.start(pem)
        yield ctx.hold(15)
        log = yield child
        assert log == 'oh noes, i am dead x_x'

    sim.start(root)
    sim.simulate(20)


def test_join_all(sim):
    def root(ctx):
        def pem(ctx, i):
            yield ctx.hold(i)
            ctx.exit(i)

        # start many child processes and let them hold for a while. The first
        # child holds the longest time.
        processes = [ctx.start(pem, i) for i in reversed(range(10))]

        # hold until all children have been terminated.
        results = []
        for process in processes:
            results.append((yield process))
        assert results == list(reversed(range(10)))

        # The first child should have terminated at timestep 9. Confirm!
        assert ctx.now == 9

    sim.start(root)
    sim.simulate(20)


def test_join_any(sim):
    def root(ctx):
        def pem(ctx, i):
            yield ctx.hold(i)
            ctx.exit(i)

        # start many child processes and let them hold for a while. The first
        # child holds the longest time.
        processes = [ctx.start(pem, i) for i in reversed(range(10))]

        def join_any(ctx, processes):
            for process in processes:
                ctx.signal(process)
            try:
                yield
                assert False, 'There should have been an interrupt'
            except Interrupt as e:
                ctx.exit(e.cause)

        # hold until the a child has terminated.
        first_dead = yield ctx.start(join_any, processes)
        # Confirm that the child created at last has terminated as first.
        assert ctx.now == 0
        assert first_dead == processes[-1]
        assert first_dead.result == 0

    sim.start(root)
    sim.simulate(20)


def test_crashing_process(sim):
    def root(ctx):
        yield ctx.hold(1)
        raise RuntimeError("That's it, I'm done")

    try:
        sim.start(root)
        sim.simulate(20)
        assert False, 'Fishy!! This is not supposed to happen!'
    except RuntimeError as exc:
        assert exc.args[0] == "That's it, I'm done"


def test_crashing_child_process(sim):
    def root(ctx):
        def panic(ctx):
            yield ctx.hold(1)
            raise RuntimeError('Oh noes, roflcopter incoming... BOOM!')

        try:
            yield ctx.start(panic)
            assert False, "Hey, where's the roflcopter?"
        except Failure as exc:
            cause = exc.__cause__
            assert type(cause) == RuntimeError
            assert cause.args[0] == 'Oh noes, roflcopter incoming... BOOM!'

    sim.start(root)
    sim.simulate(20)


def test_crashing_child_traceback(sim):
    def root(ctx):
        def panic(ctx):
            yield ctx.hold(1)
            raise RuntimeError('Oh noes, roflcopter incoming... BOOM!')

        try:
            yield ctx.start(panic)
            assert False, "Hey, where's the roflcopter?"
        except Failure as exc:
            import traceback
            stacktrace = traceback.format_exc()
            # The original exception cause (the raise in the child process) ...
            assert 'raise RuntimeError' in stacktrace
            assert type(exc.__cause__) is RuntimeError
            # ...as well as the current frame must be visible in the
            # stacktrace.
            assert 'yield ctx.start(panic)' in stacktrace

    sim.start(root)
    sim.simulate(20)


def test_illegal_suspend(sim):
    def root(ctx):
        ctx.hold(1)
        yield

    try:
        sim.start(root)
        sim.simulate(20)
        assert False, 'Expected an exception.'
    except AssertionError as exc:
        assert exc.args[0].startswith('Next event already scheduled!')


def test_illegal_hold_followed_by_join(sim):
    def root(ctx):
        def child(ctx):
            yield ctx.hold(1)

        ctx.hold(1)
        yield ctx.start(child)

    try:
        sim.start(root)
        sim.simulate(20)
        assert False, 'Expected an exception.'
    except AssertionError as exc:
        assert exc.args[0].startswith('Next event already scheduled!')


def test_invalid_schedule(sim):
    def root(ctx):
        yield 'this will not work'

    try:
        sim.start(root)
        sim.simulate(20)
        assert False, 'Expected an exception.'
    except AssertionError as exc:
        assert exc.args[0] == 'Invalid yield value "this will not work"'


def test_resume_before_start(sim):
    """A process must be started before any there can be any interaction.

    As a consequence you can't resume or interrupt a just started process as
    shown in this test. See :func:`test_immediate_resume` for the correct way
    to immediately resume a started process.
    """
    def root(ctx):
        def child(ctx):
            yield ctx.hold(1)

        c = ctx.start(child)
        ctx.resume(c)
        yield ctx.exit()

    try:
        sim.start(root)
        sim.simulate(20)
        assert False, 'This must fail'
    except AssertionError as exc:
        assert exc.args[0] == 'Process(1, child) is not initialized'


def test_immediate_resume(sim, log):
    def root(ctx, log):
        def child(ctx, log):
            yield
            log.append(ctx.now)

        def resumer(ctx, other):
            ctx.resume(other)
            yield ctx.exit()

        c = ctx.start(child, log)
        ctx.start(resumer, c)
        yield ctx.exit()

    sim.start(root, log)
    sim.simulate(20)
    # Confirm that child has been interrupted immediately at timestep 0.
    assert log == [0]


def test_signal(sim):
    """Only the most recently scheduled signal of multiple concurrent ones is
    used.

    *root* wants to be signalled if any of its three children terminate.
    Because each *child* terminates at the same time, there will be only one
    interrupt.

    # FIXME Figure out if this is good or bad...
    """
    def root(ctx):
        def child(ctx):
            yield ctx.exit()

        children = [ctx.start(child) for i in range(3)]
        for child in children:
            ctx.signal(child)

        try:
            yield
        except Interrupt as exc:
            assert exc.cause == children[-1]

    sim.start(root)
    sim.simulate(20)


def test_suspend_interrupt(ctx):
    """Tests that an interrupt is not raised in a suspended process. The cause
    of the interrupt is passed directly into the process."""

    def child(ctx):
        # Suspend this process.
        value = yield
        ctx.exit(value)

    child_proc = ctx.start(child)
    # Wait until child has started.
    yield ctx.hold(0)
    # Interrupt child_proc and use 'cake' as the cause.
    ctx.interrupt(child_proc, 'cake')
    result = yield child_proc

    assert result == 'cake'


def test_interrupt_chain_suspend(ctx):
    """Tests the handling of interrupt chaining while the victim is suspended.
    """

    def interruptor(ctx, process, id):
        yield ctx.hold(1)
        ctx.interrupt(process, id)

    # Start ten processes which will interrupt ourselves after one timestep.
    for i in range(10):
        ctx.start(interruptor, ctx.active_process, i)

    # Check that no interrupts are raised if we are suspended. Instead the
    # interrupt cause is passed directly into this process.
    log = []
    for i in range(10):
        value = yield
        log.append(value)

    assert log == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_interrupted_join(ctx):
    """Tests that interrupts are raised while the victim is waiting for another
    process."""

    def interruptor(ctx, process):
        yield ctx.hold(1)
        ctx.interrupt(process)

    def child(ctx):
        yield ctx.hold(2)

    ctx.start(interruptor, ctx.active_process)
    try:
        yield ctx.start(child)
        assert False, 'Excepted an interrupt'
    except Interrupt as interrupt:
        pass
