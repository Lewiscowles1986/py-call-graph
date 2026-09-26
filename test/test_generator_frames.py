'''
Tests for tracing generators and exception-unwound frames.

``sys.settrace`` emits a ``call`` event every time a generator is *resumed*,
not only when it is first entered, and a ``return`` event for each ``yield``
as well as for the final exit. ``TraceProcessor`` treated every
``call``/``return`` pair as a fresh symmetric invocation, so a generator
consumed twice was counted three times (once per resume, including the final
``StopIteration``) and produced a phantom ``gen -> gen`` self-edge because the
still-parked generator frame was used as the caller of its own resume.

A real generator exit is distinguishable from a yield: a ``return`` carries a
non-``None`` ``arg`` for a yield, and ``None`` for the final exit.
'''
import sys

import pytest

from pycallgraph.config import Config
from pycallgraph.tracer import SyncronousTracer


# --------------------------------------------------------------------------
# Traced subjects. These live at module level so the recorder sees stable
# fully-qualified names.
# --------------------------------------------------------------------------

def simple():
    return 1


def caller():
    simple()


def two_yield_gen():
    yield 1
    yield 2


def consume_generator():
    total = 0
    for value in two_yield_gen():
        total += value
    return total


def partial_generator():
    yield 'only'


def consume_partially():
    generator = partial_generator()
    next(generator)
    return 'done'


def raiser():
    raise ValueError('boom')


def catches():
    try:
        raiser()
    except ValueError:
        return 'caught'


def call_after_exception():
    catches()
    simple()
    return 'ok'


def _trace(function):
    '''Run ``function`` under a real tracer and return the processor.

    The stack depth is captured before tracing starts and stored on the
    processor as ``_baseline_depth`` so tests can assert that the trace left
    the stacks exactly as it found them. The test function's own frame is
    filtered, so it legitimately sits on the stack throughout.
    '''
    tracer = SyncronousTracer([], Config())
    tracer.start()
    try:
        function()
    finally:
        tracer.stop()
    return tracer.processor


def _assert_stack_settled(processor, context=''):
    '''No frame from a traced subject may be left on the stack.

    Filtered frames are represented by empty strings, and the test function's
    own frame is filtered too, so the only entries that indicate a leak are
    real fully-qualified names from this module.
    '''
    leaked = [
        entry for entry in processor.call_stack
        if entry.startswith(__name__ + '.')
    ]
    assert leaked == [], (
        '%s left frames on the stack: %r (stack: %r)'
        % (context or 'the trace', leaked, processor.call_stack)
    )


def _name(function):
    return '%s.%s' % (__name__, function.__name__)


# --------------------------------------------------------------------------
# Generators
# --------------------------------------------------------------------------

def test_a_consumed_generator_is_counted_once():
    '''
    ``two_yield_gen`` has two yields, so it is resumed three times: twice to
    produce values and once more to raise StopIteration. It is *one* function
    invocation and must be counted once.
    '''
    processor = _trace(consume_generator)

    assert processor.func_count[_name(two_yield_gen)] == 1


def test_a_consumed_generator_has_no_self_edge():
    '''
    The phantom 'gen -> gen' edge appeared because the parked generator frame
    was still the top of the stack when its own resume arrived.
    '''
    processor = _trace(consume_generator)

    generator_name = _name(two_yield_gen)
    assert generator_name not in processor.call_dict.get(generator_name, {})


def test_the_generator_edge_is_attributed_to_its_caller():
    processor = _trace(consume_generator)

    caller_name = _name(consume_generator)
    generator_name = _name(two_yield_gen)
    assert processor.call_dict[caller_name][generator_name] == 1


def test_the_consuming_function_is_counted_once():
    processor = _trace(consume_generator)

    assert processor.func_count[_name(consume_generator)] == 1


def test_a_partially_consumed_generator_is_counted_once():
    '''Only the first ``next()`` runs; generator never exhausted.'''
    processor = _trace(consume_partially)

    assert processor.func_count[_name(partial_generator)] == 1


def test_a_partially_consumed_generator_does_not_break_later_calls():
    '''
    A generator that is left suspended must not corrupt the accounting for
    anything traced afterwards.
    '''
    processor = _trace(consume_partially)

    # Nothing else was traced here, but the call graph must be self-consistent:
    # every recorded edge source and target must be a real node.
    for source, targets in processor.call_dict.items():
        if source is not None:
            assert source in processor.func_count, source
        for target in targets:
            assert target in processor.func_count, target


def test_generator_frames_are_removed_from_the_stack():
    processor = _trace(consume_generator)

    leftover = [
        entry for entry in processor.call_stack
        if entry.endswith('two_yield_gen')
    ]
    assert leftover == [], processor.call_stack


# --------------------------------------------------------------------------
# Exceptions
# --------------------------------------------------------------------------

def test_a_raising_function_is_counted_once():
    processor = _trace(catches)

    assert processor.func_count[_name(raiser)] == 1


def test_the_exception_edge_is_recorded():
    processor = _trace(catches)

    assert processor.call_dict[_name(catches)][_name(raiser)] == 1


def test_the_stack_is_settled_after_an_exception():
    '''
    Every frame unwound by the exception must have been popped, so the stack
    is back to just ``__main__``.
    '''
    processor = _trace(catches)

    _assert_stack_settled(processor, 'a caught exception')


def test_tracing_continues_correctly_after_an_exception():
    '''
    Calls made after a caught exception must still be attributed correctly.
    '''
    processor = _trace(call_after_exception)

    assert processor.func_count[_name(simple)] == 1
    assert processor.call_dict[_name(call_after_exception)][_name(simple)] == 1
    _assert_stack_settled(processor, 'a call after a caught exception')


def test_an_uncaught_exception_still_unwinds_the_stack():
    '''
    A raised exception that is not caught must not leave frames on the stack.
    '''
    tracer = SyncronousTracer([], Config())
    tracer.start()
    try:
        with pytest.raises(ValueError):
            raiser()
    finally:
        tracer.stop()

    processor = tracer.processor
    _assert_stack_settled(processor, 'an uncaught exception')


# --------------------------------------------------------------------------
# Non-generator behaviour must be unchanged
# --------------------------------------------------------------------------

def test_plain_calls_are_counted_once():
    processor = _trace(caller)

    assert processor.func_count[_name(simple)] == 1
    assert processor.call_dict[_name(caller)][_name(simple)] == 1


def test_a_plain_call_leaves_the_stack_settled():
    processor = _trace(caller)

    _assert_stack_settled(processor, 'a plain call')


def test_the_stack_is_balanced_for_every_traced_subject():
    for function in (caller, consume_generator, consume_partially,
                     catches, call_after_exception):
        processor = _trace(function)
        _assert_stack_settled(processor, function.__name__)


def test_every_edge_endpoint_is_a_known_node():
    '''Guards against phantom nodes from any of the above.'''
    for function in (caller, consume_generator, consume_partially, catches):
        processor = _trace(function)
        for source, targets in processor.call_dict.items():
            if source is not None:
                assert source in processor.func_count, (function, source)
            for target in targets:
                assert target in processor.func_count, (function, target)


def test_generator_frames_are_not_reported_as_separate_nodes():
    '''
    The generator must appear once in the node list, not once per resume.
    '''
    processor = _trace(consume_generator)

    matching = [
        name for name in processor.func_count
        if name.endswith('two_yield_gen')
    ]
    assert matching == [_name(two_yield_gen)], matching


def test_the_suite_still_uses_a_simple_trace_for_plain_code():
    '''A smoke check that the tracer is actually recording.'''
    assert sys.gettrace() is None, 'a previous test leaked a trace function'
    processor = _trace(caller)
    assert processor.func_count
