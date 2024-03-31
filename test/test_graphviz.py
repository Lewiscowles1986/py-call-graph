import os
import pytest
from calls import one_nop
from pycallgraph.output.graphviz import GraphvizOutput
from pycallgraph.pycallgraph import PyCallGraph


@pytest.fixture
def graphviz(temp):
    g = GraphvizOutput()
    g.output_file = temp
    g.output_type = 'dot'
    return g


def test_simple(graphviz):
    with PyCallGraph(output=graphviz):
        one_nop()
    dot = open(graphviz.output_file).read()
    os.unlink(graphviz.output_file)

    assert 'digraph G' in dot
    assert '__main__ -> "calls.one_nop"' in dot
