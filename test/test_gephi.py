import pytest
from pycallgraph import PyCallGraph
from pycallgraph.output.gephi import GephiOutput
from calls import one_nop


@pytest.fixture
def gephi(tmp_path):
    g = GephiOutput()
    g.output_file = str(tmp_path / 'pycallgraph.gdf')
    return g


def test_simple(gephi):
    with PyCallGraph(output=gephi):
        one_nop()
    with open(gephi.output_file) as handle:
        generated = handle.read()

    assert 'nodedef> name VARCHAR' in generated
    assert 'edgedef> node1 VARCHAR, node2 VARCHAR' in generated
    assert 'calls.one_nop,calls.one_nop,calls,1' in generated
    assert 'calls.one_nop,calls.nop,1' in generated
