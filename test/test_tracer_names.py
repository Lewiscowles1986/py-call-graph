'''
Tests for the spelling aliases on the tracer classes.

``SyncronousTracer`` and ``AsyncronousTracer`` misspell "Synchronous"
and "Asynchronous". The names are public: they are exported from
``pycallgraph.tracer``, returned by ``PyCallGraph.get_tracer_class()``, and
used as headings in the API docs, so they cannot simply be renamed.

Correctly spelled aliases are provided instead, and the historical names keep
working.
'''
import inspect
import os

from pycallgraph.config import Config
from pycallgraph.pycallgraph import PyCallGraph
from pycallgraph.tracer import (
    AsyncronousTracer,
    SynchronousTracer,
    SyncronousTracer,
    AsynchronousTracer,
)


def test_synchronous_alias_is_the_same_class():
    assert SynchronousTracer is SyncronousTracer


def test_asynchronous_alias_is_the_same_class():
    assert AsynchronousTracer is AsyncronousTracer


def test_aliases_are_exported_from_the_package_root():
    import pycallgraph

    assert pycallgraph.SynchronousTracer is SyncronousTracer
    assert pycallgraph.AsynchronousTracer is AsyncronousTracer


def test_legacy_names_still_resolve():
    '''Existing code importing the misspelled names must keep working.'''
    assert issubclass(AsyncronousTracer, SyncronousTracer)


def test_get_tracer_class_returns_the_same_objects():
    '''The spelling is irrelevant to the returned object's identity.'''
    graph = PyCallGraph(config=Config(threaded=False))
    assert graph.get_tracer_class() is SyncronousTracer

    graph = PyCallGraph(config=Config(threaded=True))
    assert graph.get_tracer_class() is AsyncronousTracer


def test_the_aliases_have_the_expected_names():
    '''
    A reader of a traceback should see the name they used, so ``__name__``
    stays as the historical class name.
    '''
    assert SynchronousTracer.__name__ == 'SyncronousTracer'
    assert AsynchronousTracer.__name__ == 'AsyncronousTracer'


def test_the_aliases_are_documented_in_the_api_reference():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo_root, 'docs', 'api', 'tracer.rst')) as handle:
        docs = handle.read()

    assert 'SynchronousTracer' in docs
    assert 'AsynchronousTracer' in docs


def test_tracing_still_works_through_the_alias(tmp_path):
    '''The aliases must be usable, not just present.'''
    from pycallgraph.output import Output

    class Counter(Output):
        def __init__(self, **kwargs):
            self.done_count = 0
            Output.__init__(self, **kwargs)

        def done(self):
            self.done_count += 1

    output = Counter()

    def work():
        return 1

    tracer = SynchronousTracer([output], Config())
    tracer.start()
    try:
        work()
    finally:
        tracer.stop()

    assert tracer.processor.func_count


def test_the_alias_is_explained_in_the_module():
    '''
    Someone grepping for the correct spelling should find why the old one
    exists, so it is not "fixed" by a future maintainer and silently broken.
    '''
    import pycallgraph.tracer as tracer_module
    source = inspect.getsource(tracer_module)

    assert 'Syncronous' in source
    assert 'misspell' in source.lower() or 'spell' in source.lower()
