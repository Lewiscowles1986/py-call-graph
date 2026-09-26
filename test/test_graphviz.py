import pytest
from calls import one_nop
from pycallgraph.output.graphviz import GraphvizOutput
from pycallgraph.pycallgraph import PyCallGraph


@pytest.fixture
def graphviz(tmp_path):
    g = GraphvizOutput()
    g.output_file = str(tmp_path / 'pycallgraph.dot')
    g.output_type = 'dot'
    return g


def test_simple(graphviz):
    with PyCallGraph(output=graphviz):
        one_nop()
    with open(graphviz.output_file) as handle:
        dot = handle.read()

    assert 'digraph G' in dot
    assert '__main__ -> "calls.one_nop"' in dot
