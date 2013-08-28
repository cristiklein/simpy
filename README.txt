SimPy
=====

SimPy is a process-based discrete-event simulation framework based on standard
Python. Its event dispatcher is based on Python’s `generators`__ and can also be
used for asynchronous networking or to implement multi-agent systems (with
both, simulated and real communication).

Processes in SimPy are simple Python generator functions and are used to model
active components like customers, vehicles or agents. SimPy also provides
various types of shared *resource* to model limited capacity congestion points
(like servers, checkout counters and tunnels). It will also provides monitoring
capabilities to aid in gathering statistics about resources and processes.

Simulations can be performed “as fast as possible”, in real time (wall clock
time) or by manually stepping through the events.

The distribution contains in-depth documentation, tutorials, and a large number
of examples.

Simpy is released under the GNU LGPL. Simulation model developers are
encouraged to share their SimPy modeling techniques with the SimPy community.
Please post a message to the `SimPy-Users mailing list`__.

__ http://docs.python.org/2/glossary.html#term-generator
__ http://lists.sourceforge.net/lists/listinfo/simpy-users


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
    ...         yield env.timeout(1)
    ...
    >>> env = simpy.Environment()
    >>> env.start(clock(env))
    <Process(clock) object at 0x...>
    >>> env.run(until=3)
    0
    1
    2


Installation
------------

SimPy requires Python 2.7, 3.2, PyPy 2.0 or above.

You can install SimPy easily via `PIP <http://pypi.python.org/pypi/pip>`_::

    $ pip install -U SimPy

You can also download and install SimPy manually::

    $ cd where/you/put/simpy/
    $ python setup.py install

To run SimPy’s test suite on your installation, execute::

    $ python -c "import simpy; simpy.test()"


Getting started
---------------

If you’ve never used SimPy before, the `SimPy tutorial
<https://simpy.readthedocs.org/en/latest/simpy_intro/index.html>`_ is a good
starting point for you. You can also try out some of the `Examples <https://simpy.readthedocs.org/en/latest/examples/index.html>`_ shipped with SimPy.


Documentation and Help
----------------------

In our `online documentation <https://simpy.readthedocs.org/>`_, you can find
`a tutorial <https://simpy.readthedocs.org/en/latest/simpy_intro/index.html>`_,
`examples <https://simpy.readthedocs.org/en/latest/examples/index.html>`_,
`topical guides
<https://simpy.readthedocs.org/en/latest/topical_guides/index.html>`_ and an
`API reference
<https://simpy.readthedocs.org/en/latest/api_reference/index.html>`_, as well
as some information about `SimPy and its history
<https://simpy.readthedocs.org/en/latest/about/index.html>`_.  For more help,
contact the `SimPy-Users mailing list
<mailto:simpy-users@lists.sourceforge.net>`_. SimPy users are pretty helpful.

If you find any bugs, please post them on our `issue tracker
<https://bitbucket.org/simpy/simpy/issues?status=new&status=open>`_.


Enjoy simulation programming in SimPy!
