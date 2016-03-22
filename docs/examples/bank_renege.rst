===========
Bank Renege
===========

Covers:

- Resources: Resource
- Condition events

A counter with a random service time and customers who renege. Based on the
program bank08.py from TheBank tutorial of SimPy 2. (KGM)

This example models a bank counter and customers arriving t random times. Each
customer has a certain patience. It waits to get to the counter until she’s at
the end of her tether. If she gets to the counter, she uses it for a while
before releasing it.

New customers are created by the ``source`` process every few time steps.

.. literalinclude:: code/bank_renege.py

The simulation's output:

.. literalinclude:: code/bank_renege.out
