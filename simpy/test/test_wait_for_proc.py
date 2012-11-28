"""
Tests for waiting for a process to finish.

"""
import pytest

from simpy import Interrupt, simulate


def test_wait_for_proc(env):
    """A process can wait until another process finishes."""
    def finisher(env):
        yield env.timeout(5)

    def waiter(env, finisher):
        proc = env.start(finisher(env))
        yield proc  # Waits until "proc" finishes

        assert env.now == 5

    env.start(waiter(env, finisher))
    simulate(env)


def test_exit(env):
    """Processes can set a return value via an ``exit()`` function,
    comparable to ``sys.exit()``.

    """
    def child(env):
        yield env.timeout(1)
        env.exit(env.now)

    def parent(env):
        result1 = yield env.start(child(env))
        result2 = yield env.start(child(env))

        assert [result1, result2] == [1, 2]

    env.start(parent(env))
    simulate(env)


@pytest.mark.skipif('sys.version_info[:2] < (3, 3)')
def test_return_value(env):
    """Processes can set a return value."""
    # Python < 3.2 would raise a SyntaxError if this was real code ...
    code = """def child(env):
        yield env.timeout(1)
        return env.now
    """
    globs, locs = {}, {}
    code = compile(code, '<string>', 'exec')
    eval(code, globs, locs)
    child = locs['child']

    def parent(env):
        result1 = yield env.start(child(env))
        result2 = yield env.start(child(env))

        assert [result1, result2] == [1, 2]

    env.start(parent(env))
    simulate(env)


def test_child_exception(env):
    """A child catches an exception and sends it to its parent."""
    def child(env):
        try:
            yield env.timeout(1)
            raise RuntimeError('Onoes!')
        except RuntimeError as err:
            env.exit(err)

    def parent(env):
        result = yield env.start(child(env))
        assert isinstance(result, Exception)

    env.start(parent(env))
    simulate(env)


def test_interrupted_join(env):
    """Tests that interrupts are raised while the victim is waiting for
    another process. The victim should get unregistered from the other
    process.

    """
    def interruptor(env, process):
        yield env.timeout(1)
        process.interrupt()

    def child(env):
        yield env.timeout(2)

    def parent(env):
        child_proc = env.start(child(env))
        try:
            yield child_proc
            pytest.fail('Did not receive an interrupt.')
        except Interrupt:
            assert env.now == 1
            assert child_proc.is_alive

            # We should not get resumed when child terminates.
            yield env.timeout(5)
            assert env.now == 6

    parent_proc = env.start(parent(env))
    env.start(interruptor(env, parent_proc))
    simulate(env)


def test_interrupted_join_and_rejoin(env):
    """Tests that interrupts are raised while the victim is waiting for
    another process. The victim tries to join again.

    """
    def interruptor(env, process):
        yield env.timeout(1)
        process.interrupt()

    def child(env):
        yield env.timeout(2)

    def parent(env):
        child_proc = env.start(child(env))
        try:
            yield child_proc
            pytest.fail('Did not receive an interrupt.')
        except Interrupt:
            assert env.now == 1
            assert child_proc.is_alive

            yield child_proc
            assert env.now == 2

    parent_proc = env.start(parent(env))
    env.start(interruptor(env, parent_proc))
    simulate(env)


def test_unregister_after_interrupt(env):
    """If a process is interrupted while waiting for another one, it
    should be unregistered from that process.

    """
    def interruptor(env, process):
        yield env.timeout(1)
        process.interrupt()

    def child(env):
        yield env.timeout(2)

    def parent(env):
        child_proc = env.start(child(env))
        try:
            yield child_proc
            pytest.fail('Did not receive an interrupt.')
        except Interrupt:
            assert env.now == 1
            assert child_proc.is_alive

        yield env.timeout(2)
        assert env.now == 3
        assert not child_proc.is_alive

    parent_proc = env.start(parent(env))
    env.start(interruptor(env, parent_proc))
    simulate(env)


def test_error_and_interrupted_join(env):
    def child_a(env, process):
        process.interrupt()
        env.exit()
        yield  # Dummy yield

    def child_b(env):
        raise AttributeError('spam')
        yield  # Dummy yield

    def parent(env):
        env.start(child_a(env, env.active_process))
        b = env.start(child_b(env))

        try:
            yield b
        # This interrupt unregisters me from b so I won't receive its
        # AttributeError
        except Interrupt:
            pass

        yield env.timeout(0)

    env.start(parent(env))
    pytest.raises(AttributeError, simulate, env)
