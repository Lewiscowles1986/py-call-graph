'''
Tests for ``Config.max_depth``.

``max_depth`` had no coverage, so its exact semantics (the comparison is
``>``, and hidden frames are pushed onto the call stack as empty strings and
therefore count towards the depth) were undocumented and unverified.
'''
import sys

import calls
from pycallgraph.config import Config
from pycallgraph.tracer import TraceProcessor


def _trace_one_nop(max_depth):
    config = Config(max_depth=max_depth)
    processor = TraceProcessor([], config)
    sys.settrace(processor.process)
    try:
        calls.one_nop()
    finally:
        sys.settrace(None)
    return processor.call_dict


def _traced_functions(call_dict):
    names = set()
    for src, callees in call_dict.items():
        if src:
            names.add(src)
        names.update(callees)
    return names


def test_max_depth_of_one_keeps_direct_callees_of_main():
    '''
    ``call_stack`` starts as ``['__main__']``, so a direct callee of
    ``__main__`` sees ``len(call_stack) == 1``. With the ``>`` comparison a
    ``max_depth`` of 1 therefore keeps it.
    '''
    call_dict = _trace_one_nop(max_depth=1)
    assert 'calls.one_nop' in _traced_functions(call_dict)


def test_max_depth_zero_prunes_everything():
    '''
    A direct callee of ``__main__`` sees ``len(call_stack) == 1``. With the
    ``>`` comparison a ``max_depth`` of 0 prunes it (``1 > 0``), so nothing
    below ``__main__`` is recorded.
    '''
    call_dict = _trace_one_nop(max_depth=0)
    assert _traced_functions(call_dict) == set()


def test_max_depth_is_the_number_of_levels_below_main():
    '''
    Verified semantics: ``max_depth = N`` keeps N levels of calls below
    ``__main__``. With ``calls.one_nop -> calls.nop`` that means depth 1 keeps
    ``one_nop`` but not ``nop``, and depth 2 keeps both.
    '''
    depth_one = _traced_functions(_trace_one_nop(max_depth=1))
    assert 'calls.one_nop' in depth_one
    assert 'calls.nop' not in depth_one

    depth_two = _traced_functions(_trace_one_nop(max_depth=2))
    assert 'calls.one_nop' in depth_two
    assert 'calls.nop' in depth_two


def test_a_low_max_depth_prunes_deeper_calls():
    call_dict = _trace_one_nop(max_depth=1)
    # calls.one_nop -> calls.nop is one level deeper and is cut off.
    assert 'calls.nop' not in _traced_functions(call_dict)


def test_a_high_max_depth_keeps_deeper_calls():
    call_dict = _trace_one_nop(max_depth=99999)
    assert 'calls.nop' in _traced_functions(call_dict)


def test_default_max_depth_is_effectively_unlimited():
    assert Config().max_depth > 100
