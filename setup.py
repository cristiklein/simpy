# coding=utf-8

from distutils.core import setup

import simpy


setup(
        name='simpy',
        version=simpy.__version__,
        packages=['simpy', 'simpy.test'],
)
