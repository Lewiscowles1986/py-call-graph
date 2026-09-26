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
        # Give the example the namespace it expects: each one ends with
        # ``if __name__ == '__main__': main()``, so __name__ must be set or
        # the entry point is silently skipped.
        exec(code, {'__name__': '__main__'}, {})
