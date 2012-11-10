import simpy


def pytest_funcarg__log(request):
    return []


def pytest_funcarg__env(request):
    return simpy.Environment()
