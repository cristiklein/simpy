=====================
Process Communication
=====================

Covers:

- Resources: Store

This example shows how to interconnect simulation model elements together using
"resources.Store" for one-to-one, and many-to-one asynchronous processes. For
one-to-many a simple BroadCastPipe class is constructed from Store.

When Useful:
  When a consumer process does not always wait on a generating process
  and these processes run asynchronously. This example shows how to
  create a buffer and also tell is the consumer process was late
  yielding to the event from a generating process.

  This is also useful when some information needs to be broadcast to
  many receiving processes

  Finally, using pipes can simplify how processes are interconnected to
  each other in a simulation model.

Example By:
  Keith Smith

.. literalinclude:: code/process_communication.py

The simulation's output:

.. literalinclude:: code/process_communication.out
