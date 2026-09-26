import re
import sys

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


def test_module_missing_file(trace_processor):
    # Use a stub module to test the missing __file__ behavior without external dependencies
    import types
    import unittest.mock as mock
    
    # Create a mock module that lacks __file__ attribute
    mock_module = types.ModuleType('mock_module')
    mock_module.__dict__.pop('__file__', None)
    
    with mock.patch.dict(sys.modules, {'mock_module': mock_module}):
        sys.settrace(trace_processor.process)
        import mock_module
        sys.settrace(None)