import pytest

from simpy import Environment, Process, Interrupt, simulate


pytest_plugins = ['simpy.test.support']


def test_join():
    env = Environment()

    def root(env):
        def pem(env):
            yield env.timeout(10)

        yield env.start(pem(env))
        assert env.now == 10

    env.start(root(env))
    simulate(env, 20)


def test_join_log():
    env = Environment()

    def root(env):
        def pem(env):
            yield env.timeout(10)
            env.exit('oh noes, i am dead x_x')
            assert False, 'Hey, i am alive? How is that possible?'

        log = yield env.start(pem(env))
        assert log == 'oh noes, i am dead x_x'

    env.start(root(env))
    simulate(env, 20)


def test_join_after_terminate(env):
    def pem(env):
        yield env.timeout(10)

    child = env.start(pem(env))
    yield env.timeout(15)
    with pytest.raises(RuntimeError) as e:
        yield child
    assert e.value.args[0] == 'Already terminated "pem"'


def test_crashing_process():
    def root(env):
        yield env.timeout(1)
        raise RuntimeError("That's it, I'm done")

    try:
        env = Environment()
        env.start(root(env))
        simulate(env, 20)
        assert False, 'Fishy!! This is not supposed to happen!'
    except RuntimeError as exc:
        assert exc.args[0] == "That's it, I'm done"


def test_crashing_child_process():
    def root(env):
        def panic(env):
            yield env.timeout(1)
            raise RuntimeError('Oh noes, roflcopter incoming... BOOM!')

        try:
            yield env.start(panic(env))
            assert False, "Hey, where's the roflcopter?"
        except RuntimeError as exc:
            assert exc.args[0] == 'Oh noes, roflcopter incoming... BOOM!'

    env = Environment()
    env.start(root(env))
    simulate(env, 20)


def test_crashing_child_traceback():
    def root(env):
        def panic(env):
            yield env.timeout(1)
            raise RuntimeError('Oh noes, roflcopter incoming... BOOM!')

        try:
            yield env.start(panic(env))
            assert False, "Hey, where's the roflcopter?"
        except RuntimeError as exc:
            import traceback
            stacktrace = traceback.format_exc()
            # The current frame must be visible in the stacktrace.
            assert 'yield env.start(panic(env))' in stacktrace

    env = Environment()
    env.start(root(env))
    simulate(env, 20)


def test_invalid_event():
    def root(env):
        yield 'this will not work'

    try:
        env = Environment()
        env.start(root(env))
        simulate(env, 20)
        assert False, 'Expected an exception.'
    except RuntimeError as exc:
        assert exc.args[0] == 'Invalid yield value "this will not work"'


def test_immediate_interrupt(env):
    def child(env, log):
        try:
            yield env.suspend()
        except Interrupt:
            log.append(env.now)

    def resumer(env, other):
        other.interrupt()
        yield env.exit()

    log = []
    c = env.start(child(env, log))
    yield env.start(resumer(env, c))

    # Confirm that child has been interrupted immediately at timestep 0.
    assert log == [0]


def test_interrupt_after_fork(env):
    def child(env):
        try:
            yield env.suspend()
        except Interrupt as i:
            assert i.cause == 'wakeup'
        env.exit('but i am so sleepy')

    c = env.start(child(env))
    c.interrupt('wakeup')
    result = yield c
    assert result == 'but i am so sleepy'


def test_interrupt_chain_after_fork(env):
    def child(env):
        for i in range(3):
            try:
                yield env.suspend()
            except Interrupt as i:
                assert i.cause == 'wakeup'
        env.exit('i am still sleepy')

    c = env.start(child(env))
    c.interrupt('wakeup')
    c.interrupt('wakeup')
    c.interrupt('wakeup')
    result = yield c
    assert result == 'i am still sleepy'


def test_interrupt_discard(env):
    """Interrupts on dead processes are discarded. If there are multiple
    concurrent interrupts on a process and the latter dies after handling the
    first interrupt, the remaining ones are silently ignored."""

    def child(env):
        try:
            yield env.suspend()
        except Interrupt as i:
            env.exit(i.cause)

    c = env.start(child(env))
    c.interrupt('first')
    c.interrupt('second')
    c.interrupt('third')

    result = yield c
    assert result == 'first'


def test_interrupt_chain(env):
    """Tests the chaining of concurrent interrupts."""

    # Interruptor processes will wait for one timestep and than interrupt the
    # given process.
    def interruptor(env, process, id):
        yield env.timeout(1)
        process.interrupt(id)

    def child(env):
        yield env.timeout(2)
        env.exit('i am done')

    # Start ten processes which will interrupt ourselves after one timestep.
    for i in range(10):
        env.start(interruptor(env, env.process, i))

    child_proc = env.start(child(env))

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


def test_suspend_interrupt(env):
    """Tests that an interrupt is not raised in a suspended process. The cause
    of the interrupt is passed directly into the process."""

    def child(env, evt):
        # Suspend this process.
        value = yield evt
        env.exit(value)

    evt = env.suspend()
    child_proc = env.start(child(env, evt))
    yield env.timeout(0)
    # Resume the event with 'cake' as value.
    evt.resume('cake')
    result = yield child_proc

    assert result == 'cake'


def test_interrupt_chain_suspend(env):
    """Tests the handling of interrupt chaining while the victim is suspended.
    """

    def interruptor(env, process, id):
        yield env.timeout(1)
        process.interrupt(id)

    # Start ten processes which will interrupt ourselves after one timestep.
    for i in range(10):
        env.start(interruptor(env, env.process, i))

    # Check that no interrupts are raised if we are suspended. Instead the
    # interrupt cause is passed directly into this process.
    log = []
    for i in range(10):
        try:
            yield env.suspend()
        except Interrupt as interrupt:
            log.append(interrupt.cause)

    assert log == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_suspend_failure(env):
    """An exception of an interrupt must be thrown into a suspended process."""

    def child(env, evt):
        evt.fail(RuntimeError('eggseptuhn!'))
        yield env.exit()

    evt = env.suspend()
    child_proc = env.start(child(env, evt))

    with pytest.raises(RuntimeError) as e:
        yield evt

    assert e.value.args[0]  == 'eggseptuhn!'


def test_interrupted_join(env):
    """Tests that interrupts are raised while the victim is waiting for another
    process."""

    def interruptor(env, process):
        yield env.timeout(1)
        process.interrupt()

    def child(env):
        yield env.timeout(2)

    env.start(interruptor(env, env.process))
    try:
        yield env.start(child(env))
        assert False, 'Excepted an interrupt'
    except Interrupt as interrupt:
        pass


def test_timeout_value(env):
    value = yield env.timeout(0, 'spam')
    assert value == 'spam'


def test_interrupted_join(env):
    """Joins can be interrupted."""
    def child(env):
        yield env.timeout(5)

    def interrupter(env, victim):
        victim.interrupt()
        yield env.exit()

    child_proc = env.start(child(env))
    env.start(interrupter(env, env.process))
    try:
        yield child_proc
        assert False, 'Expected an interrupt'
    except Interrupt as e:
        pass


def test_interrupted_join(env):
    def interrupter(env, process):
        process.interrupt()
        yield env.exit()

    def child(env):
        yield env.timeout(1)

    # Start the interrupter which will interrupt the current process while it
    # is waiting for the child process.
    env.start(interrupter(env, env.process))
    try:
        yield env.start(child(env))
    except Interrupt:
        pass

    # The interrupt will terminate the join. This process will not notice that
    # the child has terminated if it doesn't continue to wait for the child.
    yield env.timeout(2)


def test_join_interrupt(env):
    # Interrupter will interrupt the process which is currently waiting for its
    # termination.
    def interrupter(env, process):
        process.interrupt()
        yield env.timeout(1)

    interrupt_proc = env.start(interrupter(env, env.process))
    try:
        yield interrupt_proc
        assert False, 'Expected an interrupt'
    except Interrupt:
        pass

    yield interrupt_proc


def test_exit_with_process(env):
    def child(env, fork):
        yield env.exit(env.start(child(env, False)) if fork else None)

    result = yield env.start(child(env, True))

    assert type(result) is Process


def test_interrupt_self(env):
    env.process.interrupt('dude, wake up!')
    try:
        yield env.timeout(1)
        assert False, 'Expected an interrupt'
    except Interrupt as i:
        assert i.cause == 'dude, wake up!'


def test_immediate_interrupt_timeout(env):
    timeout = env.timeout(0)
    env.process.interrupt()
    try:
        yield timeout
        assert False, 'Expected an interrupt'
    except Interrupt:
        pass


def test_resumed_join(env):
    def child(env):
        yield env.exit('spam')

    proc = env.start(child(env))
    env.process.interrupt()
    try:
        result = yield proc
        assert False, 'Expected an interrupt'
    except Interrupt as i:
        pass

    result = yield proc
    assert result == 'spam'


def test_resumed_join_with_interruptor(env):
    def child(env):
        yield env.exit('spam')

    def interruptor(env, process):
        process.interrupt()
        yield env.exit()

    env.start(interruptor(env, env.process))
    proc = env.start(child(env))

    try:
        result = yield proc
        assert False, 'Expected an interrupt'
    except Interrupt as i:
        pass

    result = yield proc
    assert result == 'spam'


def test_cancelled_join(env):
    def child(env):
        yield env.timeout(1)
        yield env.exit('spam')

    proc = env.start(child(env))
    env.process.interrupt()
    try:
        result = yield proc
        assert False, 'Expected an interrupt'
    except Interrupt as i:
        pass

    yield env.timeout(2)
    assert env.now == 2


def test_shared_timeout(env):
    def child(env, timeout, id, log):
        yield timeout
        log.append((id, env.now))

    log = []
    timeout = env.timeout(1)
    # Start three children which will share the timeout event. Once that event
    # occurs all three will note their id and current time in the log.
    for i in range(3):
        env.start(child(env, timeout, i, log))
    # Now sleep long enough so that the children awake.
    yield env.timeout(1)
    assert log == [(0, 1), (1, 1), (2, 1)]


def test_illegal_timeout_resume(env):
    timeout = env.timeout(1)
    with pytest.raises(RuntimeError) as e:
        timeout.resume()

    assert e.value.args[0] == 'A timeout cannot be resumed'


def test_illegal_timeout_fail(env):
    timeout = env.timeout(1)
    with pytest.raises(RuntimeError) as e:
        timeout.fail(RuntimeError('spam'))

    assert e.value.args[0] == 'A timeout cannot be failed'


def test_resume_shared_event(env):
    def child(env, event, id, log):
        try:
            result = yield event
            log.append((id, result))
        except BaseException as e:
            log.append((id, e))

    log = []
    event = env.suspend()
    # Start some children, which will wait for the event and log its result.
    for i in range(3):
        env.start(child(env, event, i, log))

    # Let the children wait for the event.
    yield env.timeout(1)

    # Trigger the event.
    event.resume('spam')

    # Wait until the children had a chance to process the event.
    yield env.timeout(0)

    assert log == [(0, 'spam'), (1, 'spam'), (2, 'spam')]


def test_fail_shared_event(env):
    def child(env, event, id, log):
        try:
            result = yield event
            log.append((id, result))
        except BaseException as e:
            log.append((id, e))

    log = []
    event = env.suspend()
    for i in range(3):
        env.start(child(env, event, i, log))

    yield env.timeout(1)

    # Fail the event.
    exc = RuntimeError('oh noes, i haz failed')
    event.fail(exc)
    yield env.timeout(0)

    assert log == [(0, exc), (1, exc), (2, exc)]


def test_suspend_interrupt(env):
    def child(env):
        try:
            yield env.timeout(1)
        except Interrupt as i:
            assert i.cause == 1

        try:
            yield env.suspend()
        except Interrupt as i:
            assert i.cause == 2

    c = env.start(child(env))
    yield env.timeout(0)
    c.interrupt(1)
    c.interrupt(2)


def test_interrupt_exit(env):
    def child(env):
        yield env.timeout(1)

    c = env.start(child(env))
    yield env.timeout(0)
    c.interrupt('spam')

    try:
        yield c
        assert False, 'Expected an exception'
    except Interrupt as i:
        assert i.cause == 'spam'


def test_interrupted_join_failure(env):
    def child(env):
        raise RuntimeError('spam')
        yield

    def interruptor(env, process):
        process.interrupt()
        yield env.exit()

    c = env.start(child(env))
    i = env.start(interruptor(env, env.process))

    try:
        yield c
    except Interrupt:
        pass

    yield env.timeout(1)
    assert env.now == 1


def test_event_trigger(env):
    def child(env):
        yield env.exit()

    child_proc = env.start(child(env))
    evt = env.suspend()
    child_proc.joiners.append(evt.activate)
    yield evt


