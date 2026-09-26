'''
Tests for how the tracer caches module lookups.

``pycallgraph.tracer`` used to end with::

    inspect.getmodule = simple_memoize(inspect.getmodule)

That is a process-wide side effect of merely *importing* the library: it
replaces a stdlib function with an untyped, unbounded memoizer for every other
library in the process, and the cache grows without limit for the lifetime of
the interpreter.
'''
import inspect
import sys
import subprocess
import textwrap

import calls
from pycallgraph.config import Config
from pycallgraph.tracer import TraceProcessor


REPO_ROOT = __file__.rsplit('/test/', 1)[0]


def test_importing_pycallgraph_does_not_patch_inspect_getmodule():
    '''
    A fresh interpreter that imports pycallgraph must find
    ``inspect.getmodule`` unchanged.
    '''
    program = textwrap.dedent(
        '''
        import inspect
        before = inspect.getmodule
        import pycallgraph  # noqa: F401
        after = inspect.getmodule
        assert before is after, (
            'pycallgraph replaced inspect.getmodule on import: '
            '%r -> %r' % (before, after)
        )
        assert not hasattr(after, '__wrapped__'), (
            'inspect.getmodule is wrapped'
        )
        print('UNPATCHED')
        '''
    )
    result = subprocess.run(
        [sys.executable, '-c', program],
        cwd=REPO_ROOT,
        env={'PYTHONPATH': REPO_ROOT, 'PATH': ''},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert 'UNPATCHED' in result.stdout, result.stdout


def test_the_module_lookup_is_still_correct():
    '''The tracer must still map frames to their module.'''
    module = inspect.getmodule(sys._getframe())
    assert module is not None
    assert module.__name__ == __name__


def test_the_tracer_still_records_calls_after_the_change():
    '''Behaviour must be preserved: tracing still works.'''
    processor = TraceProcessor([], Config())
    sys.settrace(processor.process)
    try:
        calls.one_nop()
    finally:
        sys.settrace(None)

    assert processor.call_dict['__main__']['calls.one_nop'] == 1


def test_repeated_lookups_for_the_same_code_object_are_cached():
    '''
    The caching is what makes the change a performance win, so it should be
    kept -- just not installed globally.
    '''
    from pycallgraph.tracer import _module_for_code

    calls_to_getmodule = []
    original = inspect.getmodule

    def counting_getmodule(code):
        calls_to_getmodule.append(code)
        return original(code)

    # Clear any cached entries for the frame we are about to look up.
    frame = sys._getframe()
    code = frame.f_code

    import pycallgraph.tracer as tracer
    tracer._module_cache.pop(code, None)

    import unittest.mock as mock
    with mock.patch.object(inspect, 'getmodule', counting_getmodule):
        first = _module_for_code(code)
        second = _module_for_code(code)

    assert first is second
    assert len(calls_to_getmodule) == 1, (
        'the second lookup should have been served from the cache'
    )


def test_the_module_cache_is_shared_with_the_processor():
    '''The processor must use the same memoized lookup.'''
    import pycallgraph.tracer as tracer

    assert hasattr(tracer, '_module_for_code'), (
        'the tracer should expose an internal memoized module lookup'
    )
