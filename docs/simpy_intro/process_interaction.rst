===================
Process Interaction
===================


::

    >>> class Car(object):
    ...     def __init__(self, env):
    ...         self.env = env
    ...         self.proc = env.start(self.run())
    ...
    ...     def run(self):
    ...         while True:
    ...             print('Start parking and charging at %d' % env.now)
    ...             charge_duration = 5
    ...             yield env.start(self.charge(charge_duration))
    ...
    ...             print('Start driving at %d' % env.now)
    ...             trip_duration = 2
    ...             yield env.timeout(trip_duration)
    ...
    ...     def charge(self, duration):
    ...         yield self.env.timeout(duration)
    ...
    >>> import simpy
    >>> env = simpy.Environment()
    >>> car = Car(env)
    >>> simpy.simulate(env, until=15)
    Start parking and charging at 0
    Start driving at 5
    Start parking and charging at 7
    Start driving at 12
    Start parking and charging at 14


 ::

    >>> class Car(object):
    ...     def __init__(self, env):
    ...         self.env = env
    ...         self.proc = env.start(self.run())
    ...
    ...     def run(self):
    ...         while True:
    ...             print('Start parking and charging at %d' % env.now)
    ...             charge_duration = 5
    ...             try:
    ...                 yield env.start(self.charge(charge_duration))
    ...             except simpy.Interrupt:
    ...                 print('Was interrupted. Hope, the battery is full enough ...')
    ...
    ...             print('Start driving at %d' % env.now)
    ...             trip_duration = 2
    ...             yield env.timeout(trip_duration)
    ...
    ...     def charge(self, duration):
    ...         yield self.env.timeout(duration)
    ...
    >>> def driver(env, car):
    ...     yield env.timeout(3)
    ...     car.proc.interrupt()
    ...
    >>> env = simpy.Environment()
    >>> car = Car(env)
    >>> env.start(driver(env, car))
    Process(driver)
    >>> simpy.simulate(env, until=15)
    Start parking and charging at 0
    Was interrupted. Hope, the battery is full enough ...
    Start driving at 3
    Start parking and charging at 5
    Start driving at 10
    Start parking and charging at 12
