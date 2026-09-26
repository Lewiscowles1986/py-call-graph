.. _outputs:

Outputs
*******

Graphviz
========

This output leverages the `GraphViz <http://www.graphviz.org/>`_ graph generation tool. You'll need it to be installed before attempting to use it.

Gephi
=====

This output generates a `GDF <http://guess.wikispot.org/The_GUESS_.gdf_format>`_ file that can be used with `Gephi <https://gephi.org>`_.

Pickle
======

This output persists the completed trace so it can be loaded and rendered later without re-running the program:

.. code-block:: bash

    pycallgraph pickle --output-file callgraph.pickle -- my_script.py

.. code-block:: python

    import pickle
    with open('callgraph.pickle', 'rb') as handle:
        trace = pickle.load(handle)
    for node in trace.nodes():
        print(node.name, node.calls.value)

Only the collected trace data is persisted; the configuration and outputs are not, so a loaded trace groups functions by top-level module by default.

.. todo:: Expand this section with screenshots and examples.
