#!/usr/bin/env python

from os import path
from pathlib import Path
from setuptools import setup
import sys

from setuptools.command.test import test as TestCommand

import pycallgraph

# Only install the man page if the correct directory exists
# XXX: Commented because easy_install doesn't like it
#man_path = '/usr/share/man/man1/'
#if path.exists(man_path):
#    data_files=[['/usr/share/man/man1/', ['man/pycallgraph.1']]]
#else:
#    data_files=None

data_files=None
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

class PyTest(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)

setup(
    name='python-call-graph',
    version=pycallgraph.__version__,
    description=pycallgraph.__doc__.strip().replace('\n', ' '),
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=pycallgraph.__author__,
    author_email=pycallgraph.__email__,
    license=open('LICENSE').read(),
    url=pycallgraph.__url__,
    packages=['pycallgraph', 'pycallgraph.output'],
    scripts=['scripts/pycallgraph'],
    data_files=data_files,

    # Testing
    tests_require=['pytest'],
    cmdclass = {'test': PyTest},

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

    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Debuggers',
    ],
)

