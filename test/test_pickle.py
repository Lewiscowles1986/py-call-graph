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
from pycallgraph.output.pickle import PickleOutput
from calls import one_nop

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def pickle_output(temp):
    output = PickleOutput()
    output.output_file = temp
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
    Outputs, config and the open file handle cannot (and need not) be pickled.
    The dumped object must therefore not carry them.
    '''
    path = _record(pickle_output)

    with open(path, 'rb') as handle:
        loaded = pickle.load(handle)

    for attribute in ('outputs', 'config', 'updatables', 'lib_paths'):
        assert not hasattr(loaded, attribute)


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
