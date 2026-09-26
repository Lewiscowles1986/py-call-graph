'''
Tests for memory attribution when frames are filtered out, and for readings of
zero.

``TraceProcessor`` keeps four parallel stacks: ``call_stack``,
``call_stack_timer``, ``call_stack_memory_in`` and ``call_stack_memory_out``.
A filtered frame used to push a ``''`` sentinel onto ``call_stack`` and
``call_stack_timer`` but *not* onto the memory stacks, while the ``return``
branch popped all of them positionally. Any trace combining ``--memory`` with a
filter (the default filter excludes ``pycallgraph.*``) or ``--max-depth``
therefore attributed memory to the wrong function.

Separately, the memory-out accounting keyed off a global
``previous_event_return`` flag and a falsy check, so a measured reading of 0
was treated as "no data" and skipped the pop, drifting the stacks again.

``call_stack`` starts as ``['__main__']`` and the memory stacks start empty,
so the invariant is ``len(memory_stack) == len(call_stack) - 1``.
'''
from pycallgraph.config import Config
from pycallgraph.tracer import TraceProcessor


class FakeCode(object):
    def __init__(self, name):
        self.co_name = name


class FakeFrame(object):
    def __init__(self, name):
        self.f_code = FakeCode(name)
        self.f_locals = {}


def _name(func):
    '''The module-qualified key TraceProcessor records for a frame.'''
    return '%s.%s' % (__name__, func)


def _processor():
    # max_depth=1 makes a second-level call deterministic to filter out.
    return TraceProcessor([], Config(max_depth=1))


def _assert_stacks_in_step(processor):
    expected = len(processor.call_stack) - 1
    assert len(processor.call_stack_memory_in) == expected, (
        'memory_in is out of step with call_stack: %r vs %r'
        % (processor.call_stack_memory_in, processor.call_stack)
    )
    assert len(processor.call_stack_memory_out) == expected, (
        'memory_out is out of step with call_stack: %r vs %r'
        % (processor.call_stack_memory_out, processor.call_stack)
    )


def test_stacks_start_in_step():
    _assert_stacks_in_step(_processor())


def test_a_kept_frame_keeps_the_stacks_in_step():
    processor = _processor()
    processor.process(FakeFrame('kept'), 'call', None, memory=100)

    assert processor.call_stack == ['__main__', _name('kept')]
    _assert_stacks_in_step(processor)


def test_a_filtered_frame_keeps_the_stacks_in_step():
    processor = _processor()
    processor.process(FakeFrame('kept'), 'call', None, memory=100)
    processor.process(FakeFrame('filtered'), 'call', None, memory=200)

    assert processor.call_stack == [
        '__main__', _name('kept'), '',
    ], processor.call_stack
    _assert_stacks_in_step(processor)


def test_returning_from_a_filtered_frame_restores_the_stacks():
    processor = _processor()
    processor.process(FakeFrame('kept'), 'call', None, memory=100)
    processor.process(FakeFrame('filtered'), 'call', None, memory=200)
    processor.process(FakeFrame('filtered'), 'return', None, memory=210)

    assert processor.call_stack == ['__main__', _name('kept')]
    _assert_stacks_in_step(processor)


def test_balanced_calls_leave_the_memory_stacks_empty_again():
    processor = _processor()
    processor.process(FakeFrame('a'), 'call', None, memory=100)
    processor.process(FakeFrame('b'), 'call', None, memory=150)
    processor.process(FakeFrame('b'), 'return', None, memory=180)
    processor.process(FakeFrame('a'), 'return', None, memory=120)

    assert processor.call_stack == ['__main__']
    _assert_stacks_in_step(processor)


def test_memory_in_is_attributed_to_the_frame_that_was_entered():
    processor = _processor()
    processor.process(FakeFrame('outer'), 'call', None, memory=100)
    processor.process(FakeFrame('outer'), 'return', None, memory=140)

    assert processor.func_memory_in[_name('outer')] == 40


def test_memory_out_is_attributed_to_the_frame_that_was_entered():
    processor = _processor()
    processor.process(FakeFrame('outer'), 'call', None, memory=100)
    processor.process(FakeFrame('outer'), 'return', None, memory=140)

    assert processor.func_memory_out[_name('outer')] == 40


def test_memory_is_not_attributed_to_a_filtered_frame():
    processor = _processor()
    processor.process(FakeFrame('kept'), 'call', None, memory=100)
    processor.process(FakeFrame('filtered'), 'call', None, memory=200)
    processor.process(FakeFrame('filtered'), 'return', None, memory=260)

    assert _name('filtered') not in processor.func_memory_in
    assert _name('filtered') not in processor.func_memory_out


def test_zero_memory_readings_do_not_desynchronise_the_stacks():
    '''
    A reading of 0 is falsy. It must be treated as a real measurement so the
    stacks still pop in step.
    '''
    processor = _processor()
    processor.process(FakeFrame('func'), 'call', None, memory=0)
    _assert_stacks_in_step(processor)

    processor.process(FakeFrame('func'), 'return', None, memory=0)
    assert processor.call_stack == ['__main__']
    _assert_stacks_in_step(processor)


def test_zero_readings_produce_a_zero_delta_not_a_missing_one():
    processor = _processor()
    processor.process(FakeFrame('func'), 'call', None, memory=0)
    processor.process(FakeFrame('func'), 'return', None, memory=0)

    assert processor.func_memory_in[_name('func')] == 0
    assert processor.func_memory_out[_name('func')] == 0


def test_memory_is_not_tracked_when_it_is_not_supplied():
    '''With memory=None the stacks must stay empty throughout.'''
    processor = _processor()
    processor.process(FakeFrame('func'), 'call', None, memory=None)
    processor.process(FakeFrame('func'), 'return', None, memory=None)

    assert processor.call_stack_memory_in == []
    assert processor.call_stack_memory_out == []
