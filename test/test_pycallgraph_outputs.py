import os

from pycallgraph.config import Config
from pycallgraph.pycallgraph import PyCallGraph
from pycallgraph.output import Output

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RecordingOutput(Output):
    '''Minimal Output that counts the lifecycle calls it receives.'''

    def __init__(self, **kwargs):
        self.started = 0
        self.finished = 0
        Output.__init__(self, **kwargs)

    def start(self):
        self.started += 1

    def done(self):
        self.finished += 1


def test_output_accepts_a_single_instance():
    output = RecordingOutput()
    graph = PyCallGraph(output=output, config=Config())
    assert graph.output == [output]


def test_output_accepts_a_list():
    outputs = [RecordingOutput(), RecordingOutput()]
    graph = PyCallGraph(output=outputs, config=Config())
    assert graph.output == outputs


def test_output_accepts_a_tuple():
    outputs = (RecordingOutput(), RecordingOutput())
    graph = PyCallGraph(output=outputs, config=Config())
    assert graph.output == list(outputs)


def test_output_accepts_a_generator():
    '''
    The class documents ``output`` as "a single Output instance or an iterable
    with many of them", but it iterates the attribute at least three times.
    A generator used to be exhausted by ``reset()``, so ``start()`` started
    nothing and ``generate()`` wrote nothing -- silently.
    '''
    first, second = RecordingOutput(), RecordingOutput()
    graph = PyCallGraph(output=(o for o in (first, second)), config=Config())

    assert graph.output == [first, second]

    graph.start()
    graph.done()

    assert first.started == 1 and second.started == 1
    assert first.finished == 1 and second.finished == 1


def test_no_output_is_an_empty_list():
    graph = PyCallGraph(config=Config())
    assert graph.output == []


def test_generate_calls_every_output_once():
    outputs = [RecordingOutput(), RecordingOutput()]
    graph = PyCallGraph(output=outputs, config=Config())
    graph.done()
    assert [o.finished for o in outputs] == [1, 1]
    graph.done()
    assert [o.finished for o in outputs] == [2, 2]


def test_example_aggregators_give_examples_a_main_name():
    '''
    ``examples/*/all.py`` execute each example with ``exec(code, {}, {})``.
    Every example ends with ``if __name__ == '__main__': main()``, and
    ``__name__`` is undefined in that empty namespace, so the aggregator
    raised NameError instead of running the example.
    '''
    for aggregator in ('examples/graphviz/all.py', 'examples/gephi/all.py'):
        path = os.path.join(REPO_ROOT, aggregator)
        with open(path) as handle:
            source = handle.read()

        assert 'exec(' in source, aggregator
        assert 'exec(code, {}, {})' not in source, (
            aggregator + ' executes examples with an empty namespace, so '
            "their __main__ guard never fires"
        )
        assert "'__name__': '__main__'" in source, (
            aggregator + ' must give every example a __name__ so its '
            "__main__ guard fires"
        )
