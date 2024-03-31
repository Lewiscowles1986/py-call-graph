#!/usr/bin/env python
'''
Execute all pycallgraph examples in this directory.
'''
from glob import glob


examples = glob('*.py')
examples.remove('all.py')
for example in examples:
    print(example)
    with open(example) as file:
        source = file.read()
        code = compile(source, example, 'exec')
        exec(code, {}, {})
