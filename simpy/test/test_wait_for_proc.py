"""
Tests for waiting for a process to finish.

"""
import pytest

from simpy import Interrupt


def test_wait_for_proc(sim):
    """A process can wait until another process finishes."""
    def finisher(context):
        yield context.hold(5)

    def waiter(context, finisher):
        proc = context.start(finisher)
        yield proc  # Waits until "proc" finishes

        assert context.now == 5

    sim.start(waiter, finisher)
    sim.simulate()


def test_return_value(sim):
    """Processes can set a return value via an ``exit()`` function,
    comparable to ``sys.exit()``.

    """
    def child(context):
        yield context.hold(1)
        context.exit(context.now)

    def parent(context):
        result1 = yield context.start(child)
        result2 = yield context.start(child)

        assert [result1, result2] == [1, 2]

    sim.start(parent)
    sim.simulate()


def test_illegal_wait(sim):
    """Raise an error if a process forget to yield an event before it
    starts waiting for a process.

    """
    def child(context):
        yield context.hold(1)

    def parent(context):
        context.hold(1)
        yield context.start(child)

    sim.start(parent)
    pytest.raises(RuntimeError, sim.simulate)


def test_join_after_terminate(sim):
    """Waiting for an already terminated process should return
    immediately.

    """
    def child(context):
        yield context.hold(1)

    def parent(context):
        child_proc = context.start(child)
        yield context.hold(2)
        yield child_proc

        assert context.now == 2

    sim.start(parent)
    sim.simulate()


def test_join_all(sim):
    """Test waiting for multiple processes."""
    def child(context, i):
        yield context.hold(i)
        context.exit(i)

    def parent(context):
        processes = [context.start(child, i) for i in range(9, -1, -1)]

        # Wait for all processes to terminate.
        results = []
        for proc in processes:
            results.append((yield proc))

        assert results == list(reversed(range(10)))
        assert context.now == 9

    sim.start(parent)
    sim.simulate()


def test_join_any(sim):
    def child(context, i):
        yield context.hold(i)
        context.exit(i)

    def parent(context):
        processes = [context.start(child, i) for i in range(9, -1, -1)]

        for proc in processes:
            context.interrupt_on(proc)

        try:
            yield context.hold()
            pytest.fail('There should have been an interrupt')
        except Interrupt as interrupt:
            first_dead = interrupt.cause
            assert first_dead is processes[-1]
            assert first_dead.result == 0
            assert context.now == 0

        sim.start(parent)
        sim.simulate()


def test_child_exception(sim):
    """A child catches an exception and sends it to its parent."""
    def child(context):
        try:
            yield context.hold(1)
            raise RuntimeError('Onoes!')
        except RuntimeError as err:
            context.exit(err)

    def parent(context):
        result = yield context.start(child)
        assert isinstance(result, Exception)

    sim.start(parent)
    sim.simulate()


def test_illegal_hold_followed_by_join(sim):
    """Check that an exception is raised if a "yield proc" follows on an
    illegal hold()."""
    def child(context):
        yield context.hold(1)

    def parent(context):
        context.hold(1)
        yield context.start(child)

    sim.start(parent)
    ei = pytest.raises(RuntimeError, sim.simulate)
    # Assert that the exceptino was correctly thwon into the PEM
    assert "yield context.start(child)" in str(ei.traceback[-1])


def test_interrupt_on(sim):
    """Check async. interrupt if a process terminates."""
    def child(context):
        yield context.hold(3)
        context.exit('ohai')

    def parent(context):
        child_proc = context.start(child)
        context.interrupt_on(child_proc)

        try:
            yield context.hold()
        except Interrupt as interrupt:
            assert interrupt.cause is child_proc
            assert child_proc.result == 'ohai'
            assert context.now == 3

    sim.start(parent)
    sim.simulate()


def test_interrupted_join(sim):
    """Tests that interrupts are raised while the victim is waiting for
    another process.

    """
    def interruptor(context, process):
        yield context.hold(1)
        context.interrupt(process)

    def child(context):
        yield context.hold(2)

    def parent(context):
        child_proc = context.start(child)
        try:
            yield child_proc
            pytest.fail('Did not receive an interrupt.')
        except Interrupt:
            assert context.now == 1
            assert child_proc.is_alive

    parent_proc = sim.start(parent)
    sim.start(interruptor, parent_proc)
    sim.simulate()


def test_interrupt_on_with_join(sim):
    """Test that interrupt_on() works if a process waits for another one."""
    def child(context, i):
        yield context.hold(i)

    def parent(context):
        child_proc1 = context.start(child, 1)
        child_proc2 = context.start(child, 2)
        try:
            context.interrupt_on(child_proc1)
            yield child_proc2
        except Interrupt as interrupt:
            assert context.now == 1
            assert interrupt.cause is child_proc1
            assert child_proc2.is_alive

    sim.start(parent)
    sim.simulate()


@pytest.mark.xfail
def test_join_all_shortcut(sim):
    """Test the shortcut function to wait until a number of procs finish."""
    def child(context, i):
        yield context.hold(i)
        context.exit(i)

    def parent(context):
        processes = [context.start(child, i) for i in range(10)]

        results = yield wait_for_all(processes)

        assert results == list(range(10))
        assert context.now == 9

    sim.start(parent)
    sim.simulate()


@pytest.mark.xfail
def test_join_any_shortcut(sim):
    """Test the shortcut function to wait for any of a number of procs."""
    def child(context, i):
        yield context.hold(i)
        context.exit(i)

    def parent(context):
        processes = [context.start(child, i) for i in [4, 1, 2, 0, 3]]

        for i in range(5):
            result, processes = yield wait_for_any(processes)
            assert result == i
            assert len(processes) == (5 - i)
            assert context.now == i

    sim.start(parent)
    sim.simulate()
