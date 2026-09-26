'''
Tests for ``Config`` filter handling.

``convert_filter_args`` used to append to ``self.exclude`` in place, so any
list passed by the caller (or re-used across ``parse_args`` calls) accumulated
duplicate patterns and was mutated as a side effect.
'''
from pycallgraph.config import Config


def test_convert_filter_args_does_not_mutate_the_callers_exclude_list():
    '''
    A caller's own list must not be modified. ``append`` on the shared list
    grew it every time, and the pycallgraph exclusion leaked into the caller's
    data structure.
    '''
    exclude = ['my_module.*']
    config = Config(exclude=exclude)

    # Make the attributes convert_filter_args reads exist.
    config.include = []
    config.convert_filter_args()

    assert exclude == ['my_module.*'], 'the caller list was mutated'
    assert 'pycallgraph.*' not in exclude


def test_convert_filter_args_is_idempotent():
    '''Calling it twice must not duplicate the exclusion patterns.'''
    config = Config()
    config.include = []
    config.exclude = []

    config.convert_filter_args()
    first = list(config.exclude)
    config.convert_filter_args()

    assert config.exclude == first
    assert config.exclude.count('pycallgraph.*') == 1


def test_include_pycallgraph_skips_the_exclusion():
    config = Config()
    config.include = []
    config.exclude = []
    config.include_pycallgraph = True

    config.convert_filter_args()

    assert 'pycallgraph.*' not in config.exclude


def test_empty_include_defaults_to_everything():
    config = Config()
    config.include = []
    config.exclude = []

    config.convert_filter_args()

    assert config.include == ['*']


def test_trace_filter_reflects_the_converted_arguments():
    config = Config()
    config.include = []
    config.exclude = ['skip.*']

    config.convert_filter_args()

    assert config.trace_filter('skip.thing') is False
    assert config.trace_filter('keep.thing') is True
    assert config.trace_filter('pycallgraph.tracer') is False
