import re
import sys
import types

import pytest

import pycallgraph.tracer as tracer

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


def test_module_missing_file(trace_processor):
    '''
    Exercise the ``AttributeError`` branch for a module with no ``__file__``.

    The original test imported torch purely to obtain such a module, which made
    the whole suite hard-fail wherever torch was not installed. The tracer's
    own memoized lookup is patched instead, so the same branch is exercised
    deterministically and without any optional dependency.
    '''
    bare_module = types.ModuleType('mock_module')
    assert not hasattr(bare_module, '__file__')

    original = tracer._module_for_code
    tracer._module_for_code = lambda code: bare_module
    try:
        sys.settrace(trace_processor.process)
        calls.one_nop()
    finally:
        sys.settrace(None)
        tracer._module_for_code = original

    # The module has no __file__, so the call is filtered out by the
    # AttributeError branch rather than raising, and nothing is recorded for
    # it. (sys.settrace(None) means no return events are delivered here, so
    # the sentinels for the filtered frames remain on the stack; that is a
    # property of calling process() directly, not of this branch.)
    assert trace_processor.call_dict == {}
    assert 'mock_module' not in ''.join(trace_processor.call_stack)
