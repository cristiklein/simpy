# encoding: utf-8
"""
API tests for the interaction of multiple processes.

"""
import pytest


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


# def test_hold_not_yielded(sim):
#     """A "hold()" that is not yielded should not schedule an event."""
#     def pem(context):
#         context.hold(1)
#         yield context.start(other_pem)
#
#         assert context.now == 1
#
#     sim.start(pem)
#     pytest.raises(RuntimeError, sim.simulate)


@pytest.mark.xfail
def test_get_process_state(sim):
    """A process may be *active* (has event scheduled), *passive* (has
    no event scheduled) or *terminated* (PEM generator stopped).

    """
    def pem_a(context):
        yield context.hold(3)

    def pem_b(context, pem_a):
        yield context.hold(1)
        assert pem_a.is_alive

        yield context.hold(3)
        assert not pem_a.is_alive

    proc_a = sim.start(pem_a)
    sim.start(pem_b, proc_a)
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
