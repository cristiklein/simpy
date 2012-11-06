import inspect

import _pytest.python

from simpy.core import Environment, Infinity, step, peek


def pytest_pycollect_makeitem(collector, name, obj):
    """Collects all tests with a `env` argument as normal test. By default
    they would be collected as generator tests."""
    if collector.funcnamefilter(name) and hasattr(obj, '__call__'):
        if 'env' in _pytest.python.getfuncargnames(obj):
            return list(collector._genfunctions(name, obj))


def pytest_pyfunc_call(pyfuncitem):
    testfunction = pyfuncitem.obj
    funcargs = pyfuncitem.funcargs
    if 'env' not in funcargs: return

    env = funcargs['env']

    # Filter argument names.
    args = {}
    for arg in pyfuncitem._fixtureinfo.argnames:
        args[arg] = funcargs[arg]

    if inspect.isgeneratorfunction(testfunction):
        process = env.start(testfunction(**args))

        while process.is_alive:
            if peek(env) == Infinity:
                process.generator.throw(
                        RuntimeError('Simulation completed, but test process '
                                'has not finished yet!'))

            step(env)
    else:
        testfunction(**args)

    return True

def pytest_funcarg__env(request):
    return Environment()
