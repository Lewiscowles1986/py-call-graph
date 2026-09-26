import importlib.util
import inspect
import re
import sys
import types

import pytest

import calls
from pycallgraph.tracer import TraceProcessor
from pycallgraph.config import Config


@pytest.fixture
def trace_processor(config):
    return TraceProcessor([], config)


def test_empty(trace_processor):
    sys.settrace(trace_processor.process)
    sys.settrace(None)

    assert trace_processor.call_dict == {}


def test_nop(trace_processor):
    sys.settrace(trace_processor.process)
    calls.nop()
    sys.settrace(None)

    assert trace_processor.call_dict == {
        '__main__': {
            'calls.nop': 1
        }
    }


def test_one_nop(trace_processor):
    sys.settrace(trace_processor.process)
    calls.one_nop()
    sys.settrace(None)

    assert trace_processor.call_dict == {
        '__main__': {'calls.one_nop': 1},
        'calls.one_nop': {'calls.nop': 1},
    }


def stdlib_trace(trace_processor, include_stdlib):
    trace_processor.config = Config(include_stdlib=include_stdlib)
    sys.settrace(trace_processor.process)
    re.match("asdf", "asdf")
    calls.one_nop()
    sys.settrace(None)
    return trace_processor.call_dict


def test_no_stdlib(trace_processor):
    assert 're.match' not in stdlib_trace(trace_processor, False)


def test_yes_stdlib(trace_processor):
    assert 're.match' in stdlib_trace(trace_processor, True)


def test_module_missing_file(trace_processor, tmp_path, monkeypatch):
    '''Calls from a module without ``__file__`` are dropped, not crashed on.

    Some modules swap their own entry in ``sys.modules`` for a module-like
    object that has no ``__file__`` (``torch._VF`` does exactly this).
    ``inspect.getmodule`` then hands the tracer that object, and the tracer
    must treat it as "no usable path" rather than raising ``AttributeError``.

    This reproduces the condition directly, so the check no longer needs
    ``torch`` (and its hundreds-of-MB install) to run.
    '''
    module_path = tmp_path / 'stub_without_file.py'
    module_path.write_text(
        'def tracked():\n'
        '    return 42\n'
        '\n'
        '\n'
        'def warm_cache():\n'
        '    return None\n'
    )

    spec = importlib.util.spec_from_file_location(
        'stub_without_file', module_path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, 'stub_without_file', module)
    spec.loader.exec_module(module)

    # Resolve a *different* function first.  That teaches ``inspect`` the
    # filename -> module mapping for this file while the module still has a
    # __file__, without pinning ``tracked`` in its code -> module cache.
    # (pycallgraph wraps ``inspect.getmodule`` in an unbounded memoizer at
    # import time, so warming with ``tracked`` itself would cache the stale
    # module and never reach the branch under test.)
    inspect.getmodule(module.warm_cache.__code__)

    # Swap in a module object with no ``__file__``, as ``torch/_VF.py`` does.
    monkeypatch.setitem(
        sys.modules, 'stub_without_file',
        types.ModuleType('stub_without_file'))

    # Precondition: the tracer's lookup now resolves to an object whose
    # ``__file__`` is missing -- the branch under test.
    resolved = inspect.getmodule(module.tracked.__code__)
    assert resolved is not None
    assert not hasattr(resolved, '__file__')

    sys.settrace(trace_processor.process)
    module.tracked()
    sys.settrace(None)

    # A module without __file__ is treated as library code and dropped, so the
    # call never appears anywhere in the recorded call graph.
    recorded = [
        callee
        for callers in trace_processor.call_dict.values()
        for callee in callers
    ]
    assert not any('stub_without_file' in callee for callee in recorded)
