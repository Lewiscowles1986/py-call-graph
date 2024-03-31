#!/usr/bin/env python
'''
Execute all pycallgraph examples in this directory.
'''
from glob import glob


examples = glob('*.py')
examples.remove('all.py')
for example in examples:
    print(example)
    exec(compile(open(example).read(), example, 'exec'))
