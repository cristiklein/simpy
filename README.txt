SimPy
=====

SimPy is a process-based discrete-event simulation framework based on standard
Python. Its event dispatcher is based on Python’s `generators`__ and can also
be used for asynchronous networking or to implement multi-agent systems (with
both, simulated and real communication).

Processes in SimPy are defined by Python generator functions and can, for
example, be used to model active components like customers, vehicles or agents.
SimPy also provides various types of shared *resources* to model limited
capacity congestion points (like servers, checkout counters and tunnels).

Simulations can be performed “as fast as possible”, in real time (wall clock
time) or by manually stepping through the events.

Though it is theoretically possible to do continuous simulations with SimPy, it
has no features that help you with that. Also, SimPy is not really required for
simulations with a fixed step size and where your processes don’t interact with
each other or with shared resources.

The SimPy distribution contains tutorials, in-depth documentation, and a large
number of examples.

SimPy is released under the MIT License. Simulation model developers are
encouraged to share their SimPy modeling techniques with the SimPy community.
Please post a message to the `SimPy-Users mailing list`__.

There is an introductory talk that explains SimPy’s concepts and provides some
examples: `watch the video`__ or `get the slides`__.

__ http://docs.python.org/3/glossary.html#term-generator
__ http://lists.sourceforge.net/lists/listinfo/simpy-users
__ https://www.youtube.com/watch?v=Bk91DoAEcjY
__ http://stefan.sofa-rockers.org/downloads/simpy-ep14.pdf


A Simple Example
----------------

One of SimPy's main goals is to be easy to use. Here is an example for a simple
SimPy simulation: a *clock* process that prints the current simulation time at
each step:

.. code-block:: python

    >>> import simpy
    >>>
    >>> def clock(env, name, tick):
    ...     while True:
    ...         print(name, env.now)
    ...         yield env.timeout(tick)
    ...
    >>> env = simpy.Environment()
    >>> env.process(clock(env, 'fast', 0.5))
    <Process(clock) object at 0x...>
    >>> env.process(clock(env, 'slow', 1))
    <Process(clock) object at 0x...>
    >>> env.run(until=2)
    fast 0
    slow 0
    fast 0.5
    slow 1
    fast 1.0
    fast 1.5

Installation
------------

SimPy requires Python 2.7, 3.2, PyPy 2.0 or above.

You can install SimPy easily via `pip <http://pypi.python.org/pypi/pip>`_:

.. code-block:: bash

    $ pip install -U simpy

You can also download and install SimPy manually:

.. code-block:: bash

    $ cd where/you/put/simpy/
    $ python setup.py install

To run SimPy’s test suite on your installation, execute:

.. code-block:: bash

    $ python -c "import simpy; simpy.test()"

Of course, you can keep working with SimPy 2:

.. code-block:: bash

    $ pip install "simpy>=2.3,<3"


Getting started
---------------

If you’ve never used SimPy before, the `SimPy tutorial`__ is a good starting
point for you. You can also try out some of the `Examples`__ shipped with
SimPy.

__ https://simpy.readthedocs.org/en/latest/simpy_intro/index.html
__ https://simpy.readthedocs.org/en/latest/examples/index.html


Documentation and Help
----------------------

You can find `a tutorial`__, `examples`__, `topical guides`__ and an `API
reference`__, as well as some information about `SimPy and its history`__ in
our `online documentation`__. For more help, contact the `SimPy-Users mailing
list`__. SimPy users are pretty helpful. You can, of course, also dig through
the `source code`__.

If you find any bugs, please post them on our `issue tracker`__.

__ https://simpy.readthedocs.org/en/latest/simpy_intro/index.html
__ https://simpy.readthedocs.org/en/latest/examples/index.html
__ https://simpy.readthedocs.org/en/latest/topical_guides/index.html
__ https://simpy.readthedocs.org/en/latest/api_reference/index.html
__ https://simpy.readthedocs.org/en/latest/about/index.html
__ https://simpy.readthedocs.org/
__ mailto:simpy-users@lists.sourceforge.net
__ https://bitbucket.org/simpy/simpy/src
__ https://bitbucket.org/simpy/simpy/issues?status=new&status=open

Enjoy simulation programming in SimPy!


Ports
-----

An almost feature-complete reimplementation of SimPy in C# was written by
Andreas Beham and is available at `github.com/abeham/SimSharp`__

__ http://github.com/abeham/SimSharp
