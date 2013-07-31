=============
Event Latency
=============


Covers:

- Resources: Store

This example shows how to separate the time delay of events between processes
from the processes themselves.

When Useful:
  When modeling physical things such as cables, RF propagation, etc.  it
  better encapsulation to keep this propagation mechanism outside of the
  sending and receiving processes.

  Can also be used to interconnect processes sending messages

Example by:
  Keith Smith

.. literalinclude:: code/latency.py

The simulation's output:

.. literalinclude:: code/latency.out
