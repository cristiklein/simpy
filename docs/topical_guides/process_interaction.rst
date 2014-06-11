===================
Process Interaction
===================

Discrete event simulation is only made interesting by interactions between
processes.

So this guide is about:

* :ref:`sleep-until-woken-up` (passivate/reactivate)
* :ref:`waiting-for-another-process-to-terminate`
* :ref:`interrupting-another-process`

The first two items were already covered in the :doc:`events` guide, but we'll
also include them here for the sake of completeness.

Another possibility for processes to interact are resources. They are discussed
in a :doc:`separate guide <resources>`.


.. _sleep-until-woken-up:

Sleep until woken up
====================

Imagine you want to model an electric vehicle with an intelligent
battery-charging controller. While the vehicle is driving, the controller can
be passive but needs to be reactivate once the vehicle is connected to the
power grid in order to charge the battery.

In SimPy 2, this pattern was known as *passivate / reactivate*. In SimPy 3,
you can accomplish that with a simple, shared :class:`~simpy.events.Event`:

.. code-block:: python

   >>> from random import seed, randint
   >>> seed(23)
   >>>
   >>> import simpy
   >>>
   >>> class EV:
   ...     def __init__(self, env):
   ...         self.env = env
   ...         self.drive_proc = env.process(self.drive(env))
   ...         self.bat_ctrl_proc = env.process(self.bat_ctrl(env))
   ...         self.bat_ctrl_reactivate = env.event()
   ...
   ...     def drive(self, env):
   ...         while True:
   ...             # Drive for 20-40 min
   ...             yield env.timeout(randint(20, 40))
   ...
   ...             # Park for 1–6 hours
   ...             print('Start parking at', env.now)
   ...             self.bat_ctrl_reactivate.succeed()  # "reactivate"
   ...             self.bat_ctrl_reactivate = env.event()
   ...             yield env.timeout(randint(60, 360))
   ...             print('Stop parking at', env.now)
   ...
   ...     def bat_ctrl(self, env):
   ...         while True:
   ...             print('Bat. ctrl. passivating at', env.now)
   ...             yield self.bat_ctrl_reactivate  # "passivate"
   ...             print('Bat. ctrl. reactivated at', env.now)
   ...
   ...             # Intelligent charging behavior here …
   ...             yield env.timeout(randint(30, 90))
   ...
   >>> env = simpy.Environment()
   >>> ev = EV(env)
   >>> env.run(until=150)
   Bat. ctrl. passivating at 0
   Start parking at 29
   Bat. ctrl. reactivated at 29
   Bat. ctrl. passivating at 60
   Stop parking at 131

Since ``bat_ctrl()`` just waits for a normal event, we no longer call this
pattern *passivate / reactivate* in SimPy 3.


.. _waiting-for-another-process-to-terminate:

Waiting for another process to terminate
========================================

The example above has a problem: it may happen that the vehicles wants to park
for a shorter duration than it takes to charge the battery (this is the case if
both, charging and parking would take 60 to 90 minutes).

To fix this problem we have to slightly change our model. A new ``bat_ctrl()``
will be started every time the EV starts parking. The EV then waits until the
parking duration is over *and* until the charging has stopped:

.. code-block:: python

   >>> class EV:
   ...     def __init__(self, env):
   ...         self.env = env
   ...         self.drive_proc = env.process(self.drive(env))
   ...
   ...     def drive(self, env):
   ...         while True:
   ...             # Drive for 20-40 min
   ...             yield env.timeout(randint(20, 40))
   ...
   ...             # Park for 1–6 hours
   ...             print('Start parking at', env.now)
   ...             charging = env.process(self.bat_ctrl(env))
   ...             parking = env.timeout(randint(60, 360))
   ...             yield charging & parking
   ...             print('Stop parking at', env.now)
   ...
   ...     def bat_ctrl(self, env):
   ...         print('Bat. ctrl. started at', env.now)
   ...         # Intelligent charging behavior here …
   ...         yield env.timeout(randint(30, 90))
   ...         print('Bat. ctrl. done at', env.now)
   ...
   >>> env = simpy.Environment()
   >>> ev = EV(env)
   >>> env.run(until=310)
   Start parking at 29
   Bat. ctrl. started at 29
   Bat. ctrl. done at 83
   Stop parking at 305

Again, nothing new (if you've read the :doc:`events` guide) and special is
happening. SimPy processes are events, too, so you can yield them and will thus
wait for them to get triggered. You can also wait for two events at the same
time by concatenating them with ``&`` (see
:ref:`waiting_for_multiple_events_at_once`).


.. _interrupting-another-process:

Interrupting another process
============================

As usual, we now have another problem: Imagine, a trip is very urgent, but with
the current implementation, we always need to wait until the battery is fully
charged. If we could somehow interrupt that ...

Fortunate coincidence, there is indeed a way to do exactly this. You can call
``interrupt()`` on a :class:`~simpy.events.Process`. This will throw an
:class:`~simpy.events.Interrupt` exception into that process, resuming it
immediately:

.. code-block:: python

   >>> class EV:
   ...     def __init__(self, env):
   ...         self.env = env
   ...         self.drive_proc = env.process(self.drive(env))
   ...
   ...     def drive(self, env):
   ...         while True:
   ...             # Drive for 20-40 min
   ...             yield env.timeout(randint(20, 40))
   ...
   ...             # Park for 1 hour
   ...             print('Start parking at', env.now)
   ...             charging = env.process(self.bat_ctrl(env))
   ...             parking = env.timeout(60)
   ...             yield charging | parking
   ...             if not charging.triggered:
   ...                 # Interrupt charging if not already done.
   ...                 charging.interrupt('Need to go!')
   ...             print('Stop parking at', env.now)
   ...
   ...     def bat_ctrl(self, env):
   ...         print('Bat. ctrl. started at', env.now)
   ...         try:
   ...             yield env.timeout(randint(60, 90))
   ...             print('Bat. ctrl. done at', env.now)
   ...         except simpy.Interrupt as i:
   ...             # Onoes! Got interrupted before the charging was done.
   ...             print('Bat. ctrl. interrupted at', env.now, 'msg:',
   ...                   i.cause)
   ...
   >>> env = simpy.Environment()
   >>> ev = EV(env)
   >>> env.run(until=100)
   Start parking at 31
   Bat. ctrl. started at 31
   Stop parking at 91
   Bat. ctrl. interrupted at 91 msg: Need to go!

What ``process.interrupt()`` actually does is scheduling an
:class:`~simpy.events.Interruption` event for immediate execution. If this
event is executed it will remove the victim process' ``_resume()`` method from
the callbacks of the event that it is currently waiting for (see
:attr:`~simpy.events.Process.target`). Following that it will throw the
``Interrupt`` exception into the process.

Since we don't to anything special to the original target event of the process,
the interrupted process can yield the same event again after catching the
``Interrupt`` – Imagine someone waiting for a shop to open. The person may get
interrupted by a phone call.  After finishing the call, he or she checks if the
shop already opened and either enters or continues to wait.
