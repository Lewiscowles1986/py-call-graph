import os

import pytest

import pycallgraph
from pycallgraph import PyCallGraphException
from pycallgraph.output import GephiOutput, GraphvizOutput


def _traced(output):
    '''Build a traced function that writes to the given Output.'''
    @pycallgraph.decorators.trace(output=output)
    def traced():
        return 'traced'

    return traced


def test_trace_decorator_graphviz_output(tmp_path):
    output = GraphvizOutput(output_file=str(tmp_path / 'decorator.dot'))
    output.output_type = 'dot'

    assert _traced(output)() == 'traced'

    assert os.path.exists(output.output_file)
    assert os.path.getsize(output.output_file) > 0
    with open(output.output_file) as handle:
        assert 'digraph G' in handle.read()


def test_trace_decorator_gephi_output(tmp_path):
    output = GephiOutput(output_file=str(tmp_path / 'decorator.gdf'))

    assert _traced(output)() == 'traced'

    assert os.path.exists(output.output_file)
    assert os.path.getsize(output.output_file) > 0
    with open(output.output_file) as handle:
        assert 'nodedef> name VARCHAR' in handle.read()


def test_trace_decorator_without_output_raises():
    '''
    With no Output the decorator cannot trace, so it raises. The old tests
    called the decorated function with no assertion and wrote their files
    into the repository root.
    '''
    @pycallgraph.decorators.trace()
    def no_output():
        return 'no output'

    with pytest.raises(PyCallGraphException):
        no_output()


def test_trace_decorator_preserves_function_metadata():
    output = GraphvizOutput(output_file=os.devnull)

    @pycallgraph.decorators.trace(output=output)
    def documented():
        '''A docstring worth keeping.'''

    assert documented.__name__ == 'documented'
    assert documented.__doc__ == 'A docstring worth keeping.'


def test_trace_decorator_traces_each_call(tmp_path):
    output = GraphvizOutput(output_file=str(tmp_path / 'repeated.dot'))
    output.output_type = 'dot'

    traced = _traced(output)
    for _ in range(3):
        traced()

    assert os.path.getsize(output.output_file) > 0
