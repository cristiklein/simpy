import inspect

import _pytest.python

from simpy.core import Context, Infinity, step, peek


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

    ctx = funcargs['ctx']

    if inspect.isgeneratorfunction(testfunction):
        process = ctx.start(testfunction(**funcargs))

        while process.is_alive:
            if peek(ctx) == Infinity:
                process.generator.throw(
                        RuntimeError('Simulation completed, but test process '
                                'has not finished yet!'))

            step(ctx)
    else:
        testfunction(**funcargs)

    return True

def pytest_funcarg__ctx(request):
    return Context()
