#!/usr/bin/env python
'''
Build configuration for python-call-graph.

This module deliberately does **not** ``import pycallgraph``. Importing the
package being packaged only works when the project directory happens to be on
``sys.path``; modern build frontends (pip, build, uv) isolate the build and
remove it, which is what caused issue #29::

    ModuleNotFoundError: No module named 'pycallgraph'

Package metadata is instead read from ``pycallgraph/metadata.py`` by file path.
That file has no third-party dependencies and is the single source of truth
for the version.
'''
import os

from setuptools import find_packages
from setuptools import setup


def read_file(name):
    this_directory = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(this_directory, name), encoding='utf-8') as handle:
        return handle.read()


def read_metadata():
    '''Read ``pycallgraph/metadata.py`` without importing the package.'''
    namespace = {'__name__': 'pycallgraph.metadata'}
    try:
        exec(
            read_file(os.path.join('pycallgraph', 'metadata.py')),
            namespace,
        )
    except Exception as error:
        raise RuntimeError(
            "Could not read pycallgraph/metadata.py: %s" % error
        )
    return namespace

metadata = read_metadata()

setup(
    name='python-call-graph',
    version=metadata['__version__'],
    description=metadata['__description__'],
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    author=metadata['__author__'],
    author_email=metadata['__email__'],
    license=metadata['__license__'],
    license_files=['LICENSE'],
    url=metadata['__url__'],
    packages=find_packages(exclude=['test', 'test.*']),
    scripts=['scripts/pycallgraph'],
    python_requires='>=3.8',
    entry_points={'console_scripts': ['pycallgraph = pycallgraph.__main__:main']},

    extras_require={
        'ipython': [
            # Optional dependencies for jupyter notebooks and ipython
            'packaging',
            'ipython',
        ],
        'memory-psutil': [
            # Optional dependency for memory scanning
            'psutil',
        ],
    },

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Debuggers',
    ],
)