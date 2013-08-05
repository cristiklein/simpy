============
Machine Shop
============

Covers:

- Interrupts
- Resources: PreemptiveResource

This example comprises a workshop with *n* identical machines. A stream of jobs
(enough to keep the machines busy) arrives. Each machine breaks down
periodically. Repairs are carried out by one repairman. The repairman has
other, less important tasks to perform, too. Broken machines preempt theses
tasks. The repairman continues them when he is done with the machine repair.
The workshop works continuously.

A machine has two processes: *working* implements the actual behaviour of the
machine (producing parts). *break_machine* periodically interrupts the
*working* process to simulate the machine failure.

The repairman's other job is also a process (implemented by *other_job*). The
repairman itself is a :class:`~simpy.resources.resource.PreemptiveResource`
with a capacity of *1*. The machine repairing has a priority of *1*, while the
other job has a priority of *2* (the smaller the number, the higher the
priority).


.. literalinclude:: code/machine_shop.py

The simulation's output:

.. literalinclude:: code/machine_shop.out
