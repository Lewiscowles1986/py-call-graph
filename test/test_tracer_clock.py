'''
Tests for how ``TraceProcessor`` measures durations.

``time.time()`` is wall clock and non-monotonic: an NTP step or DST change
mid-trace can produce a negative (or wildly wrong) per-function duration.
``time.perf_counter()`` is monotonic, so it is the correct primitive.
'''
import time

from pycallgraph.config import Config
from pycallgraph.tracer import TraceProcessor


class FakeFrame(object):
    '''The minimal frame-like object ``process`` reads on a call/return.'''

    class f_code(object):
        co_name = 'demo_func'

    f_locals = {}


def _only_duration(processor):
    '''Return the single non-zero duration recorded, whatever the key.'''
    durations = [d for d in processor.func_time.values() if d > 0]
    assert len(durations) == 1, 'expected exactly one timed function'
    return durations[0]


def test_durations_do_not_read_the_wall_clock(monkeypatch):
    '''
    The tracer must not use ``time.time()`` for durations: it is not
    monotonic, so a backwards clock step yields a negative duration.
    '''
    monkeypatch.setattr(
        time, 'time', lambda: (_ for _ in ()).throw(
            AssertionError('time.time() must not be used for durations')
        ),
    )

    processor = TraceProcessor([], Config())
    frame = FakeFrame()
    processor.process(frame, 'call', None)
    time.sleep(0.005)
    processor.process(frame, 'return', None)

    assert _only_duration(processor) > 0


def test_durations_are_measured_not_assumed():
    '''Real elapsed work between call and return must be recorded.'''
    processor = TraceProcessor([], Config())
    frame = FakeFrame()

    processor.process(frame, 'call', None)
    time.sleep(0.01)
    processor.process(frame, 'return', None)

    assert _only_duration(processor) >= 0.01


def test_durations_are_never_negative():
    processor = TraceProcessor([], Config())
    frame = FakeFrame()
    processor.process(frame, 'call', None)
    processor.process(frame, 'return', None)

    for duration in processor.func_time.values():
        assert duration >= 0
