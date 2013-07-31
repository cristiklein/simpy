=====================
Gas Station Refueling
=====================

Covers:

- Resources: Resource
- Resources: Container
- Waiting for other processes


This examples models a gas station and cars that arrive at the station for
refueling.

The gas station has a limited number of fuel pumps and a fuel tank that is
shared between the fuel pumps. The gas station is thus modeled as
:class:`~simpy.resources.resource.Resource`. The shared fuel tank is modeled
with a :class:`~simpy.resources.container.Container`.

Vehicles arriving at the gas station first request a fuel pump from the
station. Once they acquire one, they try to take the desired amount of fuel
from the fuel pump. They leave when they are done.

The gas stations fuel level is reqularly monitored by *gas station control*.
When the level drops below a certain threshold, a *tank truck* is called to
refuel the gas station itself.


.. literalinclude:: code/gas_station_refuel.py

The simulation's output:

.. literalinclude:: code/gas_station_refuel.out
