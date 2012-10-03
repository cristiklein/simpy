SimPy
=====

SimPy is a process-based discrete-event simulation framework based on standard
Python and released under the GNU LGPL.

It provides the modeller with components of a simulation model. These include
processes for active components like customers, messages and vehicles as well
as  resources for passive components that form limited capacity congestion
points (like servers, checkout counters and tunnels). It also provides monitor
variables to aid in gathering statistics.

The distribution contains in-depth documentation, tutorials, and a large number
of simulation models.

Simulation model developers are encouraged to share their SimPy modeling
techniques with the SimPy community. Please post a message to the SimPy-Users
mailing list: http://lists.sourceforge.net/lists/listinfo/simpy-users

Software developers are also encouraged to interface SimPy with other Python-
accessible packages, such as GUI, database or mapping and to share these new
capabilities with the community.


A Simple Example
----------------

One of SimPy's main goals is to be easy to use. Here is an example for a simple
SimPy simulation: a *clock* process that prints the current simulation time at
each step::

    >>> import simpy
    >>>
    >>> def clock(env):
    ...     while True:
    ...         print(env.now)
    ...         yield env.hold(1)
    ...
    >>> env = simpy.Environment()
    >>> env.start(clock(env))
    Process(0, clock)
    >>> simpy.simulate(env, until=3)
    0
    1
    2


A Simple Example
----------------

This is the simplest possible for a Simpy simulation. A *clock* process prints
the current simulation time each step::

    >>> import simpy
    >>>
    >>> def clock(context):
    ...     while True:
    ...         print(context.now)
    ...         yield context.hold(1)
    ...
    >>> sim = simpy.Simulation()
    >>> sim.activate(clock)
    >>> sim.simulate(3)
    0
    1
    2


Installation
------------

SimPy requires Python 2.6 or above (including Python 3).

You can install SimPy easily via `PIP <http://pypi.python.org/pypi/pip>`_::

    $ pip install -U SimPy

You can also download and install SimPy manually::

    $ cd where/you/put/simpy/
    $ python setup.py install

To run SimPy’s test suite on your installation, execute::

    $ python -c "import simpy; simpy.test()"


Getting started
---------------

You can also run one or more of the programs under *docs/examples/* to see
whether Python finds the SimPy module. If you get an error message like
*ImportError: No module named SimPy*, check if the SimPy packages exists in
your site-packages folder (like /Lib/site-packages).

The tutorial and manuals are in the *docs/html* folder. Many users have
commented that the Bank tutorials are valuable in getting users started on
building their own simple models. Even a few lines of Python and SimPy can
model significant real systems.

For more help, contact the `SimPy-Users mailing list
<mailto:simpy-users@lists.sourceforge.net>`_. SimPy users are pretty helpful.

Enjoy simulation programming in SimPy!
