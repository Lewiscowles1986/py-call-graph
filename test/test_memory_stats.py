'''
Tests for the memory statistics exposed by ``TraceProcessor``.

``memory_in`` and ``memory_out`` previously shared a single source value, so
every output that reported memory-out (including the JSON output) published
the memory-in figure under a different key.
'''
from pycallgraph.config import Config
from pycallgraph.tracer import TraceProcessor


def _processor_with_memory():
    processor = TraceProcessor([], Config(memory=True))
    processor.func_memory_in['demo.func'] = 100
    processor.func_memory_in_max = 100
    processor.func_memory_out['demo.func'] = 7
    processor.func_memory_out_max = 7
    return processor


def test_memory_in_uses_the_memory_in_total():
    processor = _processor_with_memory()
    node = processor.stat_group_from_func('demo.func', 1)
    assert node.memory_in.value == 100


def test_memory_out_uses_the_memory_out_total():
    '''
    Regression: memory_out used to be populated from func_memory_in, so the
    two reported the same value.
    '''
    processor = _processor_with_memory()
    node = processor.stat_group_from_func('demo.func', 1)
    assert node.memory_out.value == 7


def test_memory_in_and_out_can_differ():
    processor = _processor_with_memory()
    node = processor.stat_group_from_func('demo.func', 1)
    assert node.memory_in.value != node.memory_out.value
