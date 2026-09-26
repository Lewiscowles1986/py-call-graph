'''
Acceptance tests for the pickle output.

The pickle output is meant to persist a completed trace so it can be
inspected or re-rendered later without re-running the program. Issue #28
noted that a machine-readable export was missing; these tests pin down the
*existing* pickle contract, which was completely broken:

* ``PickleOutput.done`` referenced a non-existent ``self.tracer`` and called
  ``pickle.dump`` on a module that does not export ``dump``, so using the
  output raised ``AttributeError`` and wrote nothing.
* ``TraceProcessor.__getstate__`` deleted an attribute name that no longer
  existed (``lib_path`` instead of ``lib_paths``), so even reaching the dump
  raised ``KeyError``.
'''
import pickle
import subprocess
import sys
import os

import pytest

from pycallgraph import PyCallGraph
from pycallgraph.tracer import TraceProcessor
from pycallgraph.output import outputters
from pycallgraph.output.gephi import GephiOutput
from pycallgraph.output.graphviz import GraphvizOutput
from pycallgraph.output.pickle import PickleOutput
from calls import one_nop

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def pickle_output(tmp_path):
    output = PickleOutput()
    output.output_file = str(tmp_path / 'pycallgraph.pickle')
    return output


def _record(output):
    with PyCallGraph(output=output):
        one_nop()
    return output.output_file


def test_pickle_output_writes_a_file(pickle_output):
    path = _record(pickle_output)
    assert os.path.getsize(path) > 0


def test_pickle_output_round_trips_the_trace(pickle_output):
    path = _record(pickle_output)

    with open(path, 'rb') as handle:
        loaded = pickle.load(handle)

    # The persisted payload is the trace data, not the live outputter.
    assert isinstance(loaded, TraceProcessor)
    assert loaded.func_count['calls.one_nop'] == 1
    assert loaded.call_dict['__main__']['calls.one_nop'] == 1


def test_pickle_output_omits_unpicklable_state(pickle_output):
    '''
    Outputs, the live config (it holds an argparse parser) and the open file
    handle cannot be pickled. The dumped object must carry the trace data and
    a small, picklable config stand-in instead.
    '''
    path = _record(pickle_output)

    with open(path, 'rb') as handle:
        loaded = pickle.load(handle)

    for attribute in ('outputs', 'updatables', 'lib_paths', 'is_stdlib_cache'):
        assert not hasattr(loaded, attribute)

    # 'config' is restored, but not the live Config object.
    from pycallgraph.config import Config
    assert hasattr(loaded, 'config')
    assert not isinstance(loaded.config, Config)


def test_loaded_trace_can_still_render(pickle_output):
    '''
    The help text promises a dump for 'generation later', so a loaded trace
    must still be able to build nodes and edges (this needs the grouper, which
    lives on the config of a live processor).
    '''
    path = _record(pickle_output)

    with open(path, 'rb') as handle:
        loaded = pickle.load(handle)

    nodes = {node.name: node for node in loaded.nodes()}
    assert nodes['calls.one_nop'].group == 'calls'
    assert nodes['calls.one_nop'].calls.value == 1
    edges = {(edge.src_func, edge.dst_func) for edge in loaded.edges()}
    assert ('calls.one_nop', 'calls.nop') in edges


@pytest.mark.parametrize('output_cls', [GraphvizOutput, GephiOutput])
def test_loaded_trace_can_be_rendered_by_an_output(
        pickle_output, tmp_path, output_cls):
    '''
    The real 'generation later' path: take a dump produced in one process,
    load it, and drive a normal output from it. This is what a user does to
    re-render a graph without re-running their program, and it used to fail
    with AttributeError: 'TraceProcessor' object has no attribute 'config'.
    '''
    path = _record(pickle_output)

    with open(path, 'rb') as handle:
        loaded = pickle.load(handle)

    rendered = str(tmp_path / 'rendered.out')
    output = output_cls()
    output.output_file = rendered
    output.set_processor(loaded)
    output.done()

    assert os.path.getsize(rendered) > 0


def test_pickled_state_covers_the_trace_data():
    '''
    __getstate__ uses an allowlist, so a counter added to init_trace_data is
    silently dropped from dumps unless the allowlist is updated. Guard that.
    '''
    from pycallgraph.config import Config

    processor = TraceProcessor([], Config())
    expected = set(processor._picklable_state) | {'call_dict', 'config'}
    assert set(processor.__getstate__()) == expected


def test_threaded_trace_does_not_count_calls_twice(tmp_path):
    '''
    The threaded tracer hands events to a worker thread. If the worker reuses
    a previously dequeued event when the queue is briefly empty, calls are
    counted more than once.
    '''
    from pycallgraph.config import Config
    from pycallgraph.tracer import AsyncronousTracer

    temp = str(tmp_path / 'threaded.pickle')
    output = PickleOutput()
    output.output_file = temp
    config = Config()
    config.threaded = True

    tracer = AsyncronousTracer([output], config=config)
    assert tracer.processor.func_count['calls.nop'] == 0

    with PyCallGraph(output=output, config=config):
        one_nop()

    with open(temp, 'rb') as handle:
        loaded = pickle.load(handle)

    assert loaded.func_count['calls.one_nop'] == 1
    assert loaded.func_count['calls.nop'] == 1


def test_pickle_output_is_selectable_from_the_command_line(tmp_path):
    '''
    The output class existed but was never registered, so the documented
    'pickle' output mode was rejected by the argument parser. Guard against
    it silently becoming unreachable again.
    '''
    assert 'pickle' in outputters

    temp = str(tmp_path / 'cli.pickle')
    script_path = str(tmp_path / 'cli_script.py')
    with open(script_path, 'w') as handle:
        handle.write(
            'def nop():\n'
            '    pass\n'
            '\n'
            'def one_nop():\n'
            '    nop()\n'
            '\n'
            'one_nop()\n'
        )

    env = dict(os.environ)
    env['PYTHONPATH'] = REPO_ROOT
    result = subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, 'scripts', 'pycallgraph'),
            'pickle', '-o', temp,
            '--', script_path,
        ],
        cwd=REPO_ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert result.returncode == 0, result.stdout

    with open(temp, 'rb') as handle:
        loaded = pickle.load(handle)

    # The script is exec'd by the CLI, so its functions have no module prefix.
    assert loaded.func_count['one_nop'] == 1
    assert loaded.func_count['nop'] == 1
    assert loaded.call_dict['one_nop']['nop'] == 1


def test_pickle_output_loads_in_a_fresh_interpreter(pickle_output):
    '''
    The point of pickling is to hand the trace to another process, so loading
    it in a brand new interpreter must work with nothing but pycallgraph
    importable.
    '''
    path = _record(pickle_output)

    script = (
        'import pickle, sys\n'
        'with open(sys.argv[1], "rb") as handle:\n'
        '    loaded = pickle.load(handle)\n'
        'assert loaded.func_count["calls.one_nop"] == 1\n'
        'print("LOADED")\n'
    )
    env = dict(os.environ)
    env['PYTHONPATH'] = REPO_ROOT
    result = subprocess.run(
        [sys.executable, '-c', script, path],
        cwd=REPO_ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert result.returncode == 0, result.stdout
    assert 'LOADED' in result.stdout
