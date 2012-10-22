"""
Tests for waiting for a process to finish.

"""
import pytest

from simpy import Interrupt, simulate


def test_wait_for_proc(env):
    """A process can wait until another process finishes."""
    def finisher(env):
        yield env.hold(5)

    def waiter(env, finisher):
        proc = env.start(finisher(env))
        yield proc  # Waits until "proc" finishes

        assert env.now == 5

    env.start(waiter(env, finisher))
    simulate(env)


def test_return_value(env):
    """Processes can set a return value via an ``exit()`` function,
    comparable to ``sys.exit()``.

    """
    def child(env):
        yield env.hold(1)
        env.exit(env.now)

    def parent(env):
        result1 = yield env.start(child(env))
        result2 = yield env.start(child(env))

        assert [result1, result2] == [1, 2]

    env.start(parent(env))
    simulate(env)


def test_illegal_wait(env):
    """Raise an error if a process forget to yield an event before it
    starts waiting for a process.

    """
    def child(env):
        yield env.hold(1)

    def parent(env):
        env.hold(1)
        yield env.start(child(env))

    env.start(parent(env))
    pytest.raises(RuntimeError, simulate, env)


def test_join_after_terminate(env):
    """Waiting for an already terminated process should return
    immediately.

    """
    def child(env):
        yield env.hold(1)

    def parent(env):
        child_proc = env.start(child(env))
        yield env.hold(2)
        yield child_proc

        assert env.now == 2

    env.start(parent(env))
    simulate(env)


def test_join_all(env):
    """Test waiting for multiple processes."""
    def child(env, i):
        yield env.hold(i)
        env.exit(i)

    def parent(env):
        processes = [env.start(child(env, i)) for i in range(9, -1, -1)]

        # Wait for all processes to terminate.
        results = []
        for proc in processes:
            results.append((yield proc))

        assert results == list(reversed(range(10)))
        assert env.now == 9

    env.start(parent(env))
    simulate(env)


def test_child_exception(env):
    """A child catches an exception and sends it to its parent."""
    def child(env):
        try:
            yield env.hold(1)
            raise RuntimeError('Onoes!')
        except RuntimeError as err:
            env.exit(err)

    def parent(env):
        result = yield env.start(child(env))
        assert isinstance(result, Exception)

    env.start(parent(env))
    simulate(env)


def test_illegal_hold_followed_by_join(env):
    """Check that an exception is raised if a "yield proc" follows on an
    illegal hold()."""
    def child(env):
        yield env.hold(1)

    def parent(env):
        env.hold(1)
        yield env.start(child(env))

    env.start(parent(env))
    ei = pytest.raises(RuntimeError, simulate, env)
    # Assert that the exceptino was correctly thwon into the PEM
    str_tb = str(ei.traceback[-1])
    assert "yield env.start(child(env))" in str_tb


def test_interrupted_join(env):
    """Tests that interrupts are raised while the victim is waiting for
    another process. The victim should get unregistered from the other
    process.

    """
    def interruptor(env, process):
        yield env.hold(1)
        process.interrupt()

    def child(env):
        yield env.hold(2)

    def parent(env):
        child_proc = env.start(child(env))
        try:
            yield child_proc
            pytest.fail('Did not receive an interrupt.')
        except Interrupt:
            assert env.now == 1
            assert child_proc.is_alive

            # We should not get resumed when child terminates.
            yield env.hold(5)
            assert env.now == 6

    parent_proc = env.start(parent(env))
    env.start(interruptor(env, parent_proc))
    simulate(env)


def test_interrupted_join_and_rejoin(env):
    """Tests that interrupts are raised while the victim is waiting for
    another process. The victim tries to join again.

    """
    def interruptor(env, process):
        yield env.hold(1)
        process.interrupt()

    def child(env):
        yield env.hold(2)

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

