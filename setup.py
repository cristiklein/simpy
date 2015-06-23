# encoding: utf-8
from setuptools import setup, find_packages

import simpy


setup(
    name='simpy',
    version=simpy.__version__,
    author='Ontje Lünsdorf, Stefan Scherfke',
    author_email='the_com at gmx.de; stefan at sofa-rockers.org',
    description='Event discrete, process based simulation for Python.',
    long_description='\n\n'.join(
        open(f, 'rb').read().decode('utf-8')
        for f in ['README.txt', 'CHANGES.txt', 'AUTHORS.txt']),
    url='https://simpy.rtfd.org',
    download_url='https://bitbucket.org/simpy/simpy/downloads',
    license='MIT License',
    install_requires=[],
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Scientific/Engineering',
    ],
)
