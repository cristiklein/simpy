"""
SimPy defines three kinds of resources with one or more concrete resource types
each:

- :mod:`~simpy.resources.resource`: Resources that can be used by a limited
  number of processes at a time (e.g., a gas station with a limited number of
  fuel pumps).

- :mod:`~simpy.resources.container`: Resources that model the production and
  consumption of a homogeneous, undifferentiated bulk. It may either be
  continuous (like water) or discrete (like apples).

- :mod:`~simpy.resources.store`: Resources that allow the production and
  consumption of discrete Python objects.

The :mod:`~simpy.resources.base` module defines the base classes that are used
by all resource types.

"""
