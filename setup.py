# encoding: utf-8
from distutils.core import setup

import simpy


setup(
    name='SimPy',
    version=simpy.__version__,
    author='Klaus Muller, Tony Vignaux, Ontje Lünsdorf, Stefan Scherfke',
    author_email=('vignaux at user.sourceforge.net; '
        'kgmuller at users.sourceforge.net; '
        'the_com at gmx.de; '
        'stefan at sofa-rockers.org'),
    description='Event discrete, process based simulation for Python.',
    long_description=open('README.txt').read(),
    url='https://simpy.readthedocs.org',
    download_url='https://bitbucket.org/simpy/simpy/downloads',
    license='GNU LGPL',
    packages=[
        'simpy',
        'simpy.resources',
        'simpy.test',
    ],
    package_data={},
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: GNU Library or Lesser General Public ' + \
                'License (LGPL)',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
    ],
)
