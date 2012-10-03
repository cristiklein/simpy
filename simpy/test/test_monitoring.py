# encoding: utf-8
"""
Theses test cases demonstrate the API for monitoring processes and
resources.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py*
# file
import pytest

import simpy


@pytest.mark.xfail
def test_whitebox_monitor_explicit(env):
    """*Whitebox monitoring* means, the user monitors the attributes of
    a process from within the process and has thus full access to all
    attributes.  If the process is just a envple method, the
    :class:`~simpy.Monitor` has to be passed to it when it is activated.

    """
    def pem(env, monitor):
        a = 0

        while True:
            a += env.now
            monitor.append(env.now, a)  # Explicitly collect data
            yield env.hold(1)

    monitor = simpy.Monitor()
    env.start(pem(env, monitor))
    simpy.simulate(env, 5)

    assert monitor.data == [(0, 0), (1, 1), (2, 3), (3, 6), (4, 10)]


@pytest.mark.xfail
def test_whitebox_monitor_implicit(env):
    """This is the same example as above, but shows that the monitor can
    also be configured to implictly collect data.

    """
    def pem(env, monitor):
        a = 0
        monitor.configure(lambda: a)  # Configure the monitor

        while True:
            a += env.now
            monitor.collect()  # Implicitly collect data
            yield env.hold(1)

    monitor = simpy.Monitor()
    env.start(pem(env, monitor))
    simpy.simulate(env, 5)

    assert monitor.data == [(0, 0), (1, 1), (2, 3), (3, 6), (4, 10)]


@pytest.mark.xfail
def test_whitebox_monitor_data_object(env):
    """If the *PEM* is an instance method of an object,
    a :class:`~simpy.Monitor` can be configured to automatically collect
    a nummber of instance attributes.

    """
    class Spam(object):
        def __init__(self, env):
            self.a = 0
            self.monitor = simpy.Monitor()
            self.process = env.start(self.pem)

        def pem(self, env):
            self.monitor.configure(
                    lambda: env.now,
                    lambda: self.a)
            while True:
                self.a += env.now
                self.monitor.collect()
                yield env.hold(1)

    spam = Spam(env)  # Spam.__init__ starts the PEM
    simpy.simulate(env, 5)

    assert spam.monitor.data == [(0, 0), (1, 1), (2, 3), (3, 6), (4, 10)]


@pytest.mark.xfail
def test_blackbox_monitor_processes(env):
    """A :class:`~simpy.Monitor` also provides a *PEM*
    (:meth:`Monitor.run`) that collects data from a number of objects in
    regular intervals.

    """
    class Spam(object):
        def __init__(self, env):
            self.a = 0
            self.process = env.start(self.pem)

        def pem(self, env):
            while True:
                self.a += env.now
                yield env.hold(1)

    spams = [Spam(env) for i in range(2)]
    monitor = simpy.Monitor()

    # configure also accepts a generator that creates a number of
    # collector functions:
    monitor.configure((lambda: spam.a) for spam in spams)
    env.start(monitor.run, collect_interval=1, collect_time=True)

    simpy.simulate(env, 3)
    assert monitor.data == [
            # (env.now, spam[0].a, spam[1].a)
            (0, 0, 0),
            (1, 1, 1),
            (2, 3, 3),
        ]


@pytest.mark.xfail
def test_monitor_resource_queue_length(env):
    """The number of queueing processes for a resource can be collected
    via a :class:`~simpy.Monitor` process (as in
    :func:`test_blackbox_monitor_processes`).

    """
    def pem(env, resource):
        yield resource.request()
        yield env.hold(2)
        resource.release()

    resource = simpy.Resource(1)

    env.start(pem(env, resource))
    env.start(pem(env, resource))

    monitor = simpy.Monitor()
    monitor.configure(lambda: len(resource.queue))
    # Monitor.run is a PEM that collects the configured items (and the
    # envulation time if collect_time == True) every *collect_interval*
    # steps.
    env.start(monitor.run, collect_interval=1, collect_time=True)
    simpy.simulate(env, 2)

    assert monitor.data == [(0, 0), (1, 1)]  # (time, len(queue))


@pytest.mark.xfail
def test_monitor_resource_wait_time(env):
    """There are two ways to monitor the time a process waited for (or
    used) a resource:

    1. Monitor the respective times directly in the process’ PEM.
    2. Monkeypatch request/release or put/get with some
       monitor calls.

    """
    assert False  # No test yet


@pytest.mark.xfail
def test_resource_utilization(env):
    """utilization monitoring of pumps (percent of time it’s being used)."""
    assert False  # No test yet
