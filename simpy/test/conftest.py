import simpy


def pytest_funcarg__log(request):
    return []


def pytest_funcarg__ctx(request):
    return simpy.Context()
