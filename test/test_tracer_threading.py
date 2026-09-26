import threading
import time

import pytest

from pycallgraph.config import Config
from pycallgraph.exceptions import PyCallGraphException
from pycallgraph.tracer import AsyncronousTracer, TraceProcessor


def _work():
    time.sleep(0.05)


def test_threaded_tracer_stops_the_processor():
    tracer = AsyncronousTracer([], Config(threaded=True))
    tracer.start()
    _work()
    tracer.stop()
    tracer.done()

    assert not tracer.processor.is_alive()


def test_threaded_tracer_records_the_work():
    tracer = AsyncronousTracer([], Config(threaded=True))
    tracer.start()
    _work()
    tracer.stop()
    tracer.done()

    assert tracer.processor.func_count


def _run_with_deadline(func, seconds):
    '''Run ``func`` in a thread and fail if it has not finished in time.'''
    done = threading.Event()
    error = []

    def target():
        try:
            func()
        except BaseException as exc:  # noqa: BLE001 - surfaced to the test
            error.append(exc)
        finally:
            done.set()

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    finished = done.wait(seconds)

    if error:
        raise error[0]
    return finished


def test_processor_done_does_not_hang_when_the_worker_has_died():
    '''
    ``TraceProcessor.done()`` waits for the queue to drain before signalling
    shutdown. If the worker thread has already stopped there is nobody left
    to drain it, so the wait used to spin forever.
    '''
    processor = TraceProcessor([], Config(threaded=True))

    # Put work on the queue that nobody will ever consume, and make sure the
    # worker is not running.
    processor.queue(None, 'call', None, None)
    processor.keep_going = False

    finished = _run_with_deadline(processor.done, seconds=5)
    assert finished, 'TraceProcessor.done() hung waiting for a dead worker'


def test_async_tracer_done_is_bounded_and_reports_a_stuck_processor():
    '''
    ``AsyncronousTracer.done()`` joins the processor with no timeout, so a
    stuck processor blocks the user's program forever with no diagnostics.
    It should give up and say so.
    '''
    class StuckProcessor(TraceProcessor):
        '''A processor that never finishes draining.'''

        def run(self):
            while True:
                time.sleep(0.05)

        def done(self):
            # Deliberately does not wake the worker.
            pass

    tracer = AsyncronousTracer([], Config(threaded=True))
    tracer.processor = StuckProcessor([], Config(threaded=True))
    tracer.processor.start()
    tracer.shutdown_timeout = 0.2

    try:
        assert tracer.processor.is_alive()
        with pytest.raises(PyCallGraphException):
            tracer.done()
    finally:
        tracer.processor.keep_going = False
        # Let the daemon thread die with the interpreter.
