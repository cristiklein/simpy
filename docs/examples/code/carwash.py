import random

import simpy


random_seed = 42
num_machines = 2  # Number of machines in the carwash
washtime = 5  # Minutes it takes to clean a car
t_inter = 7  # Create a car every ~7 minutes
sim_time = 20  # Simulation time in minutes


class Carwash(object):
    """A carwash has a limited number of machines (``num_machines``) to
    clean cars in parallel.

    Cars have to request one of the machines. When they got one, they
    can start the washing processes and wait for it to finish (which
    takes ``washtime`` minutes).

    """
    def __init__(self, env, num_machines, washtime):
        self.env = env
        self.machine = simpy.Resource(env, num_machines)
        self.washtime = washtime

    def wash(self, car):
        """The washing processes. It takes a ``car`` processes and tries
        to clean it."""
        yield self.env.timeout(washtime)
        print("Carwashed removed %d%% of %s's dirt." %
              (random.randint(50, 99), car))


def car(env, name, cw):
    """The car process (each car has a ``name``) arrives at the carwash
    (``cw``) and requests a cleaning machine.

    It then starts the washing process, waits for it to finish and
    leaves to never come back ...

    """
    print('%s arrives at the carwash at %.2f.' % (name, env.now))
    with cw.machine.request() as request:
        yield request

        print('%s enters the carwash at %.2f.' % (name, env.now))
        yield env.start(cw.wash(name))

        print('%s leaves the carwash at %.2f.' % (name, env.now))


def setup(env, num_machines, washtime, t_inter):
    """Create a carwash, a number of initial cars and keep creating cars
    approx. every ``t_inter`` minutes."""
    # Create the carwash
    carwash = Carwash(env, num_machines, washtime)

    # Create 4 initial cars
    for i in range(4):
        env.start(car(env, 'Car %d' % i, carwash))

    # Create more cars while the simulation is running
    while True:
        yield env.timeout(random.randint(t_inter-2, t_inter+2))
        i += 1
        env.start(car(env, 'Car %d' % i, carwash))


# Setup and start the simulation
print('Check out http://youtu.be/fXXmeP9TvBg while simulating ... ;-)')
random.seed(random_seed)  # This helps reproducing the results

# Create an environment and start the setup process
env = simpy.Environment()
env.start(setup(env, num_machines, washtime, t_inter))

# Simulate!
simpy.simulate(env, until=sim_time)
