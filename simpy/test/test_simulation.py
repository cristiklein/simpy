import pytest

from simpy import Context, Process, Interrupt, simulate


pytest_plugins = ['simpy.test.support']


def test_join():
    ctx = Context()

    def root(ctx):
        def pem(ctx):
            yield ctx.wait(10)

        yield ctx.start(pem(ctx))
        assert ctx.now == 10

    ctx.start(root(ctx))
    simulate(ctx, 20)


def test_join_log():
    ctx = Context()

    def root(ctx):
        def pem(ctx):
            yield ctx.wait(10)
            ctx.exit('oh noes, i am dead x_x')
            assert False, 'Hey, i am alive? How is that possible?'

        log = yield ctx.start(pem(ctx))
        assert log == 'oh noes, i am dead x_x'

    ctx.start(root(ctx))
    simulate(ctx, 20)


def test_join_after_terminate(ctx):
    def pem(ctx):
        yield ctx.wait(10)

    child = ctx.start(pem(ctx))
    yield ctx.wait(15)
    with pytest.raises(RuntimeError) as e:
        yield child
    assert e.value.args[0] == 'Already terminated "pem"'


def test_crashing_process():
    def root(ctx):
        yield ctx.wait(1)
        raise RuntimeError("That's it, I'm done")

    try:
        ctx = Context()
        ctx.start(root(ctx))
        simulate(ctx, 20)
        assert False, 'Fishy!! This is not supposed to happen!'
    except RuntimeError as exc:
        assert exc.args[0] == "That's it, I'm done"


def test_crashing_child_process():
    def root(ctx):
        def panic(ctx):
            yield ctx.wait(1)
            raise RuntimeError('Oh noes, roflcopter incoming... BOOM!')

        try:
            yield ctx.start(panic(ctx))
            assert False, "Hey, where's the roflcopter?"
        except RuntimeError as exc:
            assert exc.args[0] == 'Oh noes, roflcopter incoming... BOOM!'

    ctx = Context()
    ctx.start(root(ctx))
    simulate(ctx, 20)


def test_crashing_child_traceback():
    def root(ctx):
        def panic(ctx):
            yield ctx.wait(1)
            raise RuntimeError('Oh noes, roflcopter incoming... BOOM!')

        try:
            yield ctx.start(panic(ctx))
            assert False, "Hey, where's the roflcopter?"
        except RuntimeError as exc:
            import traceback
            stacktrace = traceback.format_exc()
            traceback.print_exc()
            # The current frame must be visible in the stacktrace.
            assert 'yield ctx.start(panic(ctx))' in stacktrace

    ctx = Context()
    ctx.start(root(ctx))
    simulate(ctx, 20)


def test_invalid_event():
    def root(ctx):
        yield 'this will not work'

    try:
        ctx = Context()
        ctx.start(root(ctx))
        simulate(ctx, 20)
        assert False, 'Expected an exception.'
    except RuntimeError as exc:
        assert exc.args[0] == 'Invalid yield value "this will not work"'


def test_immediate_interrupt(ctx):
    def child(ctx, log):
        try:
            yield ctx.suspend()
        except Interrupt:
            log.append(ctx.now)

    def resumer(ctx, other):
        other.interrupt()
        yield ctx.exit()

    log = []
    c = ctx.start(child(ctx, log))
    yield ctx.start(resumer(ctx, c))

    # Confirm that child has been interrupted immediately at timestep 0.
    assert log == [0]


def test_interrupt_after_fork(ctx):
    def child(ctx):
        try:
            yield ctx.suspend()
        except Interrupt as i:
            assert i.cause == 'wakeup'
        ctx.exit('but i am so sleepy')

    c = ctx.start(child(ctx))
    c.interrupt('wakeup')
    result = yield c
    assert result == 'but i am so sleepy'


def test_interrupt_chain_after_fork(ctx):
    def child(ctx):
        for i in range(3):
            try:
                yield ctx.suspend()
            except Interrupt as i:
                assert i.cause == 'wakeup'
        ctx.exit('i am still sleepy')

    c = ctx.start(child(ctx))
    c.interrupt('wakeup')
    c.interrupt('wakeup')
    c.interrupt('wakeup')
    result = yield c
    assert result == 'i am still sleepy'


def test_interrupt_discard(ctx):
    """Interrupts on dead processes are discarded. If there are multiple
    concurrent interrupts on a process and the latter dies after handling the
    first interrupt, the remaining ones are silently ignored."""

    def child(ctx):
        try:
            yield ctx.suspend()
        except Interrupt as i:
            ctx.exit(i.cause)

    c = ctx.start(child(ctx))
    c.interrupt('first')
    c.interrupt('second')
    c.interrupt('third')

    result = yield c
    assert result == 'first'


def test_interrupt_chain(ctx):
    """Tests the chaining of concurrent interrupts."""

    # Interruptor processes will wait for one timestep and than interrupt the
    # given process.
    def interruptor(ctx, process, id):
        yield ctx.wait(1)
        process.interrupt(id)

    def child(ctx):
        yield ctx.wait(2)
        ctx.exit('i am done')

    # Start ten processes which will interrupt ourselves after one timestep.
    for i in range(10):
        ctx.start(interruptor(ctx, ctx.process, i))

    child_proc = ctx.start(child(ctx))

    # Check that we are interrupted ten times while waiting for child_proc to
    # complete.
    log = []
    while child_proc.is_alive:
        try:
            value = yield child_proc
        except Interrupt as interrupt:
            value = interrupt.cause

        log.append(value)

    assert log == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'i am done']


def test_suspend_interrupt(ctx):
    """Tests that an interrupt is not raised in a suspended process. The cause
    of the interrupt is passed directly into the process."""

    def child(ctx, evt):
        # Suspend this process.
        value = yield evt
        ctx.exit(value)

    evt = ctx.suspend()
    child_proc = ctx.start(child(ctx, evt))
    yield ctx.wait(0)
    # Resume the event with 'cake' as value.
    evt.resume('cake')
    result = yield child_proc

    assert result == 'cake'


def test_interrupt_chain_suspend(ctx):
    """Tests the handling of interrupt chaining while the victim is suspended.
    """

    def interruptor(ctx, process, id):
        yield ctx.wait(1)
        process.interrupt(id)

    # Start ten processes which will interrupt ourselves after one timestep.
    for i in range(10):
        ctx.start(interruptor(ctx, ctx.process, i))

    # Check that no interrupts are raised if we are suspended. Instead the
    # interrupt cause is passed directly into this process.
    log = []
    for i in range(10):
        try:
            yield ctx.suspend()
        except Interrupt as interrupt:
            log.append(interrupt.cause)

    assert log == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_suspend_failure(ctx):
    """An exception of an interrupt must be thrown into a suspended process."""

    def child(ctx, evt):
        evt.fail(RuntimeError('eggseptuhn!'))
        yield ctx.exit()

    evt = ctx.suspend()
    child_proc = ctx.start(child(ctx, evt))

    with pytest.raises(RuntimeError) as e:
        yield evt

    assert e.value.args[0]  == 'eggseptuhn!'


def test_interrupted_join(ctx):
    """Tests that interrupts are raised while the victim is waiting for another
    process."""

    def interruptor(ctx, process):
        yield ctx.wait(1)
        process.interrupt()

    def child(ctx):
        yield ctx.wait(2)

    ctx.start(interruptor(ctx, ctx.process))
    try:
        yield ctx.start(child(ctx))
        assert False, 'Excepted an interrupt'
    except Interrupt as interrupt:
        pass


def test_wait_value(ctx):
    value = yield ctx.wait(0, 'spam')
    assert value == 'spam'


def test_interrupted_join(ctx):
    """Joins can be interrupted."""
    def child(ctx):
        yield ctx.wait(5)

    def interrupter(ctx, victim):
        victim.interrupt()
        yield ctx.exit()

    child_proc = ctx.start(child(ctx))
    ctx.start(interrupter(ctx, ctx.process))
    try:
        yield child_proc
        assert False, 'Expected an interrupt'
    except Interrupt as e:
        pass


def test_interrupted_join(ctx):
    def interrupter(ctx, process):
        process.interrupt()
        yield ctx.exit()

    def child(ctx):
        yield ctx.wait(1)

    # Start the interrupter which will interrupt the current process while it
    # is waiting for the child process.
    ctx.start(interrupter(ctx, ctx.process))
    try:
        yield ctx.start(child(ctx))
    except Interrupt:
        pass

    # The interrupt will terminate the join. This process will not notice that
    # the child has terminated if it doesn't continue to wait for the child.
    yield ctx.wait(2)


def test_join_interrupt(ctx):
    # Interrupter will interrupt the process which is currently waiting for its
    # termination.
    def interrupter(ctx, process):
        process.interrupt()
        yield ctx.wait(1)

    interrupt_proc = ctx.start(interrupter(ctx, ctx.process))
    try:
        yield interrupt_proc
        assert False, 'Expected an interrupt'
    except Interrupt:
        pass

    yield interrupt_proc


def test_exit_with_process(ctx):
    def child(ctx, fork):
        yield ctx.exit(ctx.start(child(ctx, False)) if fork else None)

    result = yield ctx.start(child(ctx, True))

    assert type(result) is Process


def test_interrupt_self(ctx):
    ctx.process.interrupt('dude, wake up!')
    try:
        yield ctx.wait(1)
        assert False, 'Expected an interrupt'
    except Interrupt as i:
        assert i.cause == 'dude, wake up!'


def test_immediate_interrupt_wait(ctx):
    wait = ctx.wait(0)
    ctx.process.interrupt()
    try:
        yield wait
        assert False, 'Expected an interrupt'
    except Interrupt:
        pass


def test_resumed_join(ctx):
    def child(ctx):
        yield ctx.exit('spam')

    proc = ctx.start(child(ctx))
    ctx.process.interrupt()
    try:
        result = yield proc
        assert False, 'Expected an interrupt'
    except Interrupt as i:
        pass

    result = yield proc
    assert result == 'spam'


def test_resumed_join_with_interruptor(ctx):
    def child(ctx):
        yield ctx.exit('spam')

    def interruptor(ctx, process):
        process.interrupt()
        yield ctx.exit()

    ctx.start(interruptor(ctx, ctx.process))
    proc = ctx.start(child(ctx))

    try:
        result = yield proc
        assert False, 'Expected an interrupt'
    except Interrupt as i:
        pass

    result = yield proc
    assert result == 'spam'


def test_cancelled_join(ctx):
    def child(ctx):
        yield ctx.wait(1)
        yield ctx.exit('spam')

    proc = ctx.start(child(ctx))
    ctx.process.interrupt()
    try:
        result = yield proc
        assert False, 'Expected an interrupt'
    except Interrupt as i:
        pass

    yield ctx.wait(2)
    assert ctx.now == 2


def test_shared_wait(ctx):
    def child(ctx, wait, id, log):
        yield wait
        log.append((id, ctx.now))

    log = []
    wait = ctx.wait(1)
    # Start three children which will share the wait event. Once that event
    # occurs all three will note their id and current time in the log.
    for i in range(3):
        ctx.start(child(ctx, wait, i, log))
    # Now sleep long enough so that the children awake.
    yield ctx.wait(1)
    assert log == [(0, 1), (1, 1), (2, 1)]


def test_illegal_wait_resume(ctx):
    wait = ctx.wait(1)
    with pytest.raises(RuntimeError) as e:
        wait.resume()

    assert e.value.args[0] == 'A timeout cannot be resumed'


def test_illegal_wait_fail(ctx):
    wait = ctx.wait(1)
    with pytest.raises(RuntimeError) as e:
        wait.fail(RuntimeError('spam'))

    assert e.value.args[0] == 'A timeout cannot be failed'


def test_resume_shared_event(ctx):
    def child(ctx, event, id, log):
        try:
            result = yield event
            log.append((id, result))
        except BaseException as e:
            log.append((id, e))

    log = []
    event = ctx.suspend()
    # Start some children, which will wait for the event and log its result.
    for i in range(3):
        ctx.start(child(ctx, event, i, log))

    # Let the children wait for the event.
    yield ctx.wait(1)

    # Trigger the event.
    event.resume('spam')

    # Wait until the children had a chance to process the event.
    yield ctx.wait(0)

    assert log == [(0, 'spam'), (1, 'spam'), (2, 'spam')]


def test_fail_shared_event(ctx):
    def child(ctx, event, id, log):
        try:
            result = yield event
            log.append((id, result))
        except BaseException as e:
            log.append((id, e))

    log = []
    event = ctx.suspend()
    for i in range(3):
        ctx.start(child(ctx, event, i, log))

    yield ctx.wait(1)

    # Fail the event.
    exc = RuntimeError('oh noes, i haz failed')
    event.fail(exc)
    yield ctx.wait(0)

    assert log == [(0, exc), (1, exc), (2, exc)]


def test_suspend_interrupt(ctx):
    def child(ctx):
        try:
            yield ctx.wait(1)
        except Interrupt as i:
            assert i.cause == 1

        try:
            yield ctx.suspend()
        except Interrupt as i:
            assert i.cause == 2

    c = ctx.start(child(ctx))
    yield ctx.wait(0)
    c.interrupt(1)
    c.interrupt(2)


def test_interrupt_exit(ctx):
    def child(ctx):
        yield ctx.wait(1)

    c = ctx.start(child(ctx))
    yield ctx.wait(0)
    c.interrupt('spam')

    try:
        yield c
        assert False, 'Expected an exception'
    except Interrupt as i:
        assert i.cause == 'spam'


def test_interrupted_join_failure(ctx):
    def child(ctx):
        raise RuntimeError('spam')
        yield

    def interruptor(ctx, process):
        process.interrupt()
        yield ctx.exit()

    c = ctx.start(child(ctx))
    i = ctx.start(interruptor(ctx, ctx.process))

    try:
        yield c
    except Interrupt:
        pass

    yield ctx.wait(1)
    assert ctx.now == 1
