import simpy


def pytest_funcarg__log(request):
    return []


def pytest_funcarg__sim(request):
    return simpy.Simulation()
