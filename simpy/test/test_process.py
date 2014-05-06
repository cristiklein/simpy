"""
Tests for the ``simpy.events.Process``.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file
import pytest

from simpy import Interrupt


def test_start_non_process(env):
    """Check that you cannot start a normal function."""
    def foo():
        pass

    pytest.raises(ValueError, env.process, foo)


def test_get_state(env):
    """A process is alive until it's generator has not terminated."""
    def pem_a(env):
        yield env.timeout(3)

    def pem_b(env, pem_a):
        yield env.timeout(1)
        assert pem_a.is_alive

        yield env.timeout(3)
        assert not pem_a.is_alive

    proc_a = env.process(pem_a(env))
    env.process(pem_b(env, proc_a))
    env.run()


def test_target(env):
    def pem(env, event):
        yield event

    event = env.timeout(5)
    proc = env.process(pem(env, event))

    # Wait until "proc" is initialized and yielded the event
    while env.peek() < 5:
        env.step()
    assert proc.target is event
    proc.interrupt()


def test_wait_for_proc(env):
    """A process can wait until another process finishes."""
    def finisher(env):
        yield env.timeout(5)

    def waiter(env, finisher):
        proc = env.process(finisher(env))
        yield proc  # Waits until "proc" finishes

        assert env.now == 5

    env.process(waiter(env, finisher))
    env.run()


def test_exit(env):
    """Processes can set a return value via an ``exit()`` function,
    comparable to ``sys.exit()``.

    """
    def child(env):
        yield env.timeout(1)
        env.exit(env.now)

    def parent(env):
        result1 = yield env.process(child(env))
        result2 = yield env.process(child(env))

        assert [result1, result2] == [1, 2]

    env.process(parent(env))
    env.run()


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
        result1 = yield env.process(child(env))
        result2 = yield env.process(child(env))

        assert [result1, result2] == [1, 2]

    env.process(parent(env))
    env.run()


def test_child_exception(env):
    """A child catches an exception and sends it to its parent."""
    def child(env):
        try:
            yield env.timeout(1)
            raise RuntimeError('Onoes!')
        except RuntimeError as err:
            env.exit(err)

    def parent(env):
        result = yield env.process(child(env))
        assert isinstance(result, Exception)

    env.process(parent(env))
    env.run()


def test_interrupted_join(env):
    """Interrupts remove a process from the callbacks of its target."""

    def interruptor(env, process):
        yield env.timeout(1)
        process.interrupt()

    def child(env):
        yield env.timeout(2)

    def parent(env):
        child_proc = env.process(child(env))
        try:
            yield child_proc
            pytest.fail('Did not receive an interrupt.')
        except Interrupt:
            assert env.now == 1
            assert child_proc.is_alive

            # We should not get resumed when child terminates.
            yield env.timeout(5)
            assert env.now == 6

    parent_proc = env.process(parent(env))
    env.process(interruptor(env, parent_proc))
    env.run()


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
        child_proc = env.process(child(env))
        try:
            yield child_proc
            pytest.fail('Did not receive an interrupt.')
        except Interrupt:
            assert env.now == 1
            assert child_proc.is_alive

            yield child_proc
            assert env.now == 2

    parent_proc = env.process(parent(env))
    env.process(interruptor(env, parent_proc))
    env.run()


def test_error_and_interrupted_join(env):
    def child_a(env, process):
        process.interrupt()
        env.exit()
        yield  # Dummy yield

    def child_b(env):
        raise AttributeError('spam')
        yield  # Dummy yield

    def parent(env):
        env.process(child_a(env, env.active_process))
        b = env.process(child_b(env))

        try:
            yield b
        # This interrupt unregisters me from b so I won't receive its
        # AttributeError
        except Interrupt:
            pass

        yield env.timeout(0)

    env.process(parent(env))
    pytest.raises(AttributeError, env.run)
