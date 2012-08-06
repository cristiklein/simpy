# encoding: utf-8
"""
Theses test cases demonstrate the API for monitoring processes and
resources.

"""
# Pytest gets the parameters "sim" and "log" from the *conftest.py*
# file
import simpy


def test_whitebox_monitor_explicit(sim):
    """*Whitebox monitoring* means, the user monitors the attributes of
    a process from within the process and has thus full access to all
    attributes.  If the process is just a simple method, the
    :class:`~simpy.Monitor` has to be passed to it when it is activated.

    """
    def pem(context, monitor):
        a = 0

        while True:
            a += context.now
            monitor.append(context.now, a)  # Explicitly collect data
            yield context.hold(1)

    monitor = simpy.Monitor()
    sim.start(pem, monitor)
    sim.simulate(5)

    assert monitor.data == [(0, 0), (1, 1), (2, 3), (3, 6), (4, 10)]


def test_whitebox_monitor_implicit(sim):
    """This is the same example as above, but shows that the monitor can
    also be configured to implictly collect data.

    """
    def pem(context, monitor):
        a = 0
        monitor.configure(lambda: a)  # Configure the monitor

        while True:
            a += context.now
            monitor.collect()  # Implicitly collect data
            yield context.hold(1)

    monitor = simpy.Monitor()
    sim.start(pem, monitor)
    sim.simulate(5)

    assert monitor.data == [(0, 0), (1, 1), (2, 3), (3, 6), (4, 10)]


def test_whitebox_monitor_data_object(sim):
    """If the *PEM* is an instance method of an object,
    a :class:`~simpy.Monitor` can be configured to automatically collect
    a nummber of instance attributes.

    """
    class Spam(object):
        def __init__(self, sim):
            self.a = 0
            self.monitor = simpy.Monitor()
            self.process = sim.start(self.pem)

        def pem(self, context):
            self.monitor.configure(
                    lambda: context.now,
                    lambda: self.a)
            while True:
                self.a += context.now
                self.monitor.collect()
                yield context.hold(1)

    spam = Spam(sim)  # Spam.__init__ starts the PEM
    sim.simulate(5)

    assert spam.monitor.data == [(0, 0), (1, 1), (2, 3), (3, 6), (4, 10)]


def test_blackbox_monitor_processes(sim):
    """A :class:`~simpy.Monitor` also provides a *PEM*
    (:meth:`Monitor.run`) that collects data from a number of objects in
    regular intervals.

    """
    class Spam(object):
        def __init__(self, sim):
            self.a = 0
            self.process = sim.start(self.pem)

        def pem(self, context):
            while True:
                self.a += context.now
                yield context.hold(1)

    spams = [Spam(sim) for i in range(2)]
    monitor = simpy.Monitor()

    # configure also accepts a generator that creates a number of
    # collector functions:
    monitor.configure((lambda: spam.a) for spam in spams)
    sim.start(monitor.run, collect_interval=1, collect_time=True)

    sim.simulate(3)
    assert monitor.data == [
            # (context.now, spam[0].a, spam[1].a)
            (0, 0, 0),
            (1, 1, 1),
            (2, 3, 3),
        ]


def test_monitor_resource_queue_length(sim):
    """The number of queueing processes for a resource can be collected
    via a :class:`~simpy.Monitor` process (as in
    :func:`test_blackbox_monitor_processes`).

    """
    def pem(context, resource):
        yield resource.request()
        yield context.hold(2)
        resource.release()

    resource = simpy.Resource(1)

    sim.start(pem, resource)
    sim.start(pem, resource)

    monitor = simpy.Monitor()
    monitor.configure(lambda: len(resource.queue))
    # Monitor.run is a PEM that collects the configured items (and the
    # simulation time if collect_time == True) every *collect_interval*
    # steps.
    sim.start(monitor.run, collect_interval=1, collect_time=True)
    sim.simulate(2)

    assert monitor.data == [(0, 0), (1, 1)]  # (time, len(queue))


def test_monitor_resource_wait_time(sim):
    """There are two ways to monitor the time a process waited for (or
    used) a resource:

    1. Monitor the respective times directly in the process’ PEM.
    2. Monkeypatch request/release or put/get with some
       monitor calls.

    """
    assert False  # No test yet


def test_resource_utilization(sim):
    """utilization monitoring of pumps (percent of time it’s being used)."""
    assert False  # No test yet
