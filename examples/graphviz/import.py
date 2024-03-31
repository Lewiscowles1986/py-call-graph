#!/usr/bin/env python
'''
This example shows the interals of certain Python modules when they are being
imported.
'''
from importlib import import_module
from pycallgraph import PyCallGraph
from pycallgraph import Config
from pycallgraph.output import GraphvizOutput


def main():
    import_list = (
        'pickle',
        'html.parser',
        'urllib',
    )
    graphviz = GraphvizOutput()
    config = Config(include_stdlib=True)

    for module in import_list:
        graphviz.output_file = 'import-{}.png'.format(module)
        with PyCallGraph(output=graphviz, config=config):
            import_module(module)


if __name__ == '__main__':
    main()
