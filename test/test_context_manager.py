'''
Tests for the :class:`PyCallGraph` context manager protocol.

``__enter__`` returned ``None`` (so ``with PyCallGraph(...) as graph:`` bound
``graph`` to ``None``), and every ``__exit__`` ran the outputs again, so a
context that was exited more than once rendered the graph more than once.
'''
import pytest

from pycallgraph.config import Config
from pycallgraph.exceptions import PyCallGraphException
from pycallgraph.output import Output
from pycallgraph.pycallgraph import PyCallGraph


class CountingOutput(Output):
    '''Records how many times it is started and finished.'''

    def __init__(self, **kwargs):
        self.started = 0
        self.finished = 0
        Output.__init__(self, **kwargs)

    def start(self):
        self.started += 1

    def done(self):
        self.finished += 1


def test_enter_returns_the_graph():
    with PyCallGraph(output=CountingOutput(), config=Config()) as graph:
        assert graph is not None
        assert isinstance(graph, PyCallGraph)


def test_enter_returns_a_usable_graph():
    output = CountingOutput()
    with PyCallGraph(output=output, config=Config()) as graph:
        assert graph.config is not None
        assert graph.output == [output]


def test_exit_writes_the_output():
    output = CountingOutput()
    with PyCallGraph(output=output, config=Config()):
        pass
    assert output.finished == 1


def test_exit_is_idempotent():
    '''Exiting twice must not render the output twice.'''
    output = CountingOutput()
    graph = PyCallGraph(output=output, config=Config())

    graph.__enter__()
    graph.__exit__(None, None, None)
    assert output.finished == 1

    graph.__exit__(None, None, None)
    assert output.finished == 1, 'a second __exit__ re-ran the outputs'


def test_exit_after_a_plain_done_does_not_repeat():
    output = CountingOutput()
    graph = PyCallGraph(output=output, config=Config())

    graph.done()
    assert output.finished == 1
    graph.__exit__(None, None, None)
    assert output.finished == 1


def test_reentering_traces_again():
    '''A second ``with`` block must start a new trace.'''
    output = CountingOutput()
    graph = PyCallGraph(output=output, config=Config())

    with graph:
        pass
    with graph:
        pass

    assert output.started == 2
    assert output.finished == 2


def test_exception_in_the_body_still_writes_the_output():
    output = CountingOutput()
    with pytest.raises(ValueError):
        with PyCallGraph(output=output, config=Config()):
            raise ValueError('boom')

    assert output.finished == 1


def test_exception_is_not_suppressed_by_the_context_manager():
    '''``__exit__`` returns a falsy value, so exceptions propagate.'''
    output = CountingOutput()
    graph = PyCallGraph(output=output, config=Config())

    result = graph.__exit__(ValueError, ValueError('boom'), None)
    assert not result


def test_enter_without_outputs_raises():
    graph = PyCallGraph(config=Config())
    with pytest.raises(PyCallGraphException):
        graph.__enter__()
