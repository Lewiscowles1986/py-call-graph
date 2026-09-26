'''
Tests for the memory sampling backend.

The vendored ``memory_profiler`` falls back to ``ps v`` on POSIX when psutil
is missing, but ``ps v`` uses the BSD format on macOS, where the ``RSS`` column
does not exist. The bare ``except`` returns -1, so every sample became a
negative number with no indication that measurement had failed.
'''
import warnings

import pytest

import pycallgraph.memory_profiler as memory_profiler
from pycallgraph.config import Config
from pycallgraph.tracer import SyncronousTracer


class _Output(object):
    '''Stand-in output (no lifecycle methods are used here).'''

    def should_update(self):
        return False


def _tracer(monkeypatch, sample):
    monkeypatch.setattr(
        memory_profiler, 'memory_usage', lambda *a, **kw: [sample]
    )
    return SyncronousTracer([_Output()], Config(memory=True))


def test_a_failed_sample_warns(monkeypatch, recwarn):
    tracer = _tracer(monkeypatch, -1)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        tracer.memory()

    messages = [str(w.message) for w in caught]
    assert any('memory' in m.lower() for m in messages), messages


def test_a_failed_sample_is_reported_as_unknown(monkeypatch):
    '''
    A negative sample means "could not measure", so it must not be published
    as a memory figure: negative values flow into every statistic.
    '''
    tracer = _tracer(monkeypatch, -1)
    assert tracer.memory() is None


def test_a_good_sample_is_converted_to_bytes(monkeypatch):
    tracer = _tracer(monkeypatch, 1.5)
    assert tracer.memory() == 1500000


def test_zero_is_a_valid_sample(monkeypatch):
    tracer = _tracer(monkeypatch, 0)
    assert tracer.memory() == 0


def test_the_warning_is_emitted_only_once(monkeypatch):
    '''A per-event warning would flood the output of a real trace.'''
    tracer = _tracer(monkeypatch, -1)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for _ in range(5):
            tracer.memory()

    assert len(caught) == 1, [str(w.message) for w in caught]


def test_memory_is_not_sampled_when_disabled(monkeypatch):
    tracer = SyncronousTracer([_Output()], Config(memory=False))
    assert tracer.memory() is None


def test_posix_ps_fallback_reports_failure_explicitly():
    '''
    The fallback returns -1 when the platform's ``ps`` output is not parsable,
    which is the documented signal the tracer turns into "unknown".
    '''
    if not hasattr(memory_profiler, '_get_memory'):
        pytest.skip('psutil is installed, no fallback to check')

    # Whatever the platform, the fallback must either return a non-negative
    # figure or the -1 sentinel -- never raise and never invent a number.
    value = memory_profiler._get_memory(-1)
    assert value == -1 or value >= 0
