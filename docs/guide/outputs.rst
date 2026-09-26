.. _outputs:

Outputs
*******

Graphviz
========

This output leverages the `GraphViz <http://www.graphviz.org/>`_ graph generation tool. You'll need it to be installed before attempting to use it.

Gephi
=====

This output generates a `GDF <http://guess.wikispot.org/The_GUESS_.gdf_format>`_ file that can be used with `Gephi <https://gephi.org>`_.

JSON
====

This output writes the collected call graph as a single JSON document, so it can be consumed by other tooling without depending on a graph renderer.

.. code-block:: bash

    pycallgraph json --output-file callgraph.json -- my_script.py

The document is versioned and contains ``nodes`` and ``edges``:

.. code-block:: json

    {
      "version": 1,
      "nodes": [
        {"name": "my_module.main", "group": "my_module", "calls": 1,
         "time": 0.0012, "memory_in": 0, "memory_out": 0}
      ],
      "edges": [
        {"source": "my_module.main", "target": "my_module.helper",
         "calls": 2, "time": 0.0004}
      ]
    }

Edge endpoints are named ``source``/``target`` (Gephi's GDF output calls
the same fields ``node1``/``node2``).

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
