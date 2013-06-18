============
Installation
============

SimPy is implemented in pure Python and has no dependencies. SimPy runs on
Python 2 (>= 2.7) and Python 3 (>= 3.2). PyPy is also supported. If you have
`pip <http://pypi.python.org/pypi/pip>`_ installed, just type

.. code-block:: bash

    $ pip install simpy

and you are done.

Alternatively, you can `download SimPy <http://pypi.python.org/pypi/SimPy/>`_
and install it manually. Extract the archive, open a terminal window where you
extracted SimPy and type:

.. code-block:: bash

    $ python setup.py install

You can now optionally run SimPy's tests to see if everything works fine. You
need `pytest <http://pytest.org>`_ and `mock
<http://www.voidspace.org.uk/python/mock/>`_ for this:

.. code-block:: bash

    $ python -c "import simpy; simpy.test()"


Upgrading from SimPy 2
======================

If you are already familiar with SimPy 2, please read the Guide
:ref:`porting_from_simpy2`.


What's Next
===========

Now that you've installed SimPy, you probably want to simulate something. The
:ref:`next section <basic_concepts>` will introduce you to SimPy's basic
concepts.
