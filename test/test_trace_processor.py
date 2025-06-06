import re
import sys
from unittest.mock import MagicMock, patch

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
    frame = MagicMock()
    fn = MagicMock()
    fn.co_name = "test"
    frame.f_code = fn
    mock_module = MagicMock()
    mock_module.__name__ = "mocked_module"
    mock_module.__file__ = (
        property(lambda self: (_ for _ in ()).throw(
            AttributeError("No __file__ attribute")
        ))
    )
    with patch('inspect.getmodule', return_value=mock_module):
        result = trace_processor.process(frame, 'call', None, None)
        assert result is None
