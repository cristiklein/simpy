import inspect

import _pytest.python

from simpy.core import Simulation, Infinity


def pytest_pycollect_makeitem(collector, name, obj):
    """Collects all tests with a `ctx` argument as normal test. By default
    they would be collected as generator tests."""
    if collector.funcnamefilter(name) and hasattr(obj, '__call__'):
        if 'ctx' in _pytest.python.getfuncargnames(obj):
            return collector._genfunctions(name, obj)


def pytest_pyfunc_call(pyfuncitem):
    testfunction = pyfuncitem.obj
    funcargs = pyfuncitem.funcargs
    if 'ctx' not in funcargs: return

    # The context object is just a place holder and will be correctly set by
    # the simulation.start().
    del funcargs['ctx']

    simulation = Simulation()

    if inspect.isgeneratorfunction(testfunction):
        process = simulation.start(testfunction, **funcargs)

        while process.generator is not None and simulation.peek() != Infinity:
            simulation.step()
    else:
        testfunction(**funcargs)

    return True

def pytest_funcarg__ctx(request):
    # This is a no-op. The context will be set later by the simulation (see
    # pytest_pyfunc_call).
    return None
