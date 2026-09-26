'''
Tests for how :class:`GraphvizOutput` invokes the ``dot`` binary.

The output built a shell command string and ran it with ``shell=True``, so any
path or option containing shell metacharacters was interpreted by the shell,
and the ``stderr`` captured from a failed run was discarded along with the
error code.
'''
import os

import pytest

from pycallgraph.config import Config
from pycallgraph.exceptions import PyCallGraphException
from pycallgraph.output.graphviz import GraphvizOutput
from pycallgraph.tracer import TraceProcessor


class _RecordingPopen(object):
    '''Captures the argv passed to Popen and returns a chosen result.'''

    def __init__(self, returncode=0, stderr=b''):
        self.returncode = returncode
        self.stderr_bytes = stderr
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self

    def communicate(self, *args, **kwargs):
        return (b'', self.stderr_bytes)


def _output_with_trace(tmp_path):
    processor = TraceProcessor([], Config())
    processor.func_count['demo.func'] = 1
    processor.func_count_max = 1

    output = GraphvizOutput()
    output.output_file = str(tmp_path / 'graph.dot')
    output.output_type = 'dot'
    output.set_processor(processor)
    return output


def test_dot_is_not_run_through_a_shell(tmp_path, monkeypatch):
    '''``shell=True`` must not be used: paths containing spaces or shell
    metacharacters would be reinterpreted by the shell.'''
    recorder = _RecordingPopen()
    monkeypatch.setattr(
        'pycallgraph.output.graphviz.sub.Popen', recorder, raising=False)
    monkeypatch.setattr('subprocess.Popen', recorder)

    output = _output_with_trace(tmp_path)
    output.done()

    assert recorder.calls, 'dot was never executed'
    _, kwargs = recorder.calls[0]
    assert kwargs.get('shell') is not True


def test_dot_is_argv_not_a_command_string(tmp_path, monkeypatch):
    recorder = _RecordingPopen()
    monkeypatch.setattr('subprocess.Popen', recorder)

    output = _output_with_trace(tmp_path)
    output.done()

    args, _ = recorder.calls[0]
    command = args[0]
    assert isinstance(command, (list, tuple)), (
        'the command should be an argv sequence, not a shell string'
    )
    assert command[0] == 'dot'


def test_failure_surfaces_the_stderr_output(tmp_path, monkeypatch):
    '''The stderr of a failed run used to be discarded, hiding the cause.'''
    recorder = _RecordingPopen(
        returncode=1, stderr=b'dot: cannot open output file')
    monkeypatch.setattr('subprocess.Popen', recorder)

    output = _output_with_trace(tmp_path)

    with pytest.raises(PyCallGraphException) as excinfo:
        output.done()

    assert 'cannot open output file' in str(excinfo.value)


def test_failure_message_includes_the_exit_code(tmp_path, monkeypatch):
    recorder = _RecordingPopen(returncode=3, stderr=b'boom')
    monkeypatch.setattr('subprocess.Popen', recorder)

    output = _output_with_trace(tmp_path)

    with pytest.raises(PyCallGraphException) as excinfo:
        output.done()

    assert '3' in str(excinfo.value)


@pytest.mark.skipif(
    not any(
        os.path.exists(os.path.join(p, 'dot'))
        for p in os.environ.get('PATH', '').split(os.pathsep)
    ),
    reason='the graphviz dot binary is not installed',
)
def test_a_real_run_produces_a_dot_file(tmp_path):
    output = _output_with_trace(tmp_path)
    output.done()

    assert os.path.exists(output.output_file)
    assert 'digraph G' in open(output.output_file).read()


def test_temp_file_is_cleaned_up_on_success(tmp_path, monkeypatch):
    recorder = _RecordingPopen()
    monkeypatch.setattr('subprocess.Popen', recorder)

    output = _output_with_trace(tmp_path)

    import tempfile
    before = set(os.listdir(tempfile.gettempdir()))
    output.done()
    after = set(os.listdir(tempfile.gettempdir()))

    # Nothing new should remain in the temp directory.
    leftover = {
        name for name in (after - before)
        if name.startswith('tmp')
    }
    assert leftover == set(), leftover


def test_the_traced_script_is_not_executed_by_a_shell(tmp_path, monkeypatch):
    '''
    Guards the specific hazard: an output path containing shell syntax must be
    passed through verbatim rather than interpreted.
    '''
    recorder = _RecordingPopen()
    monkeypatch.setattr('subprocess.Popen', recorder)

    output = _output_with_trace(tmp_path)
    # A filename that would be dangerous under shell=True.
    output.output_file = str(tmp_path / 'weird $(echo pwned).dot')
    output.done()

    args, _ = recorder.calls[0]
    command = args[0]
    assert any('$(echo pwned)' in part for part in command), (
        'the output path should be passed as a single argv element'
    )
