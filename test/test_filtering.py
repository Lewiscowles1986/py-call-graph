'''
Tests for ``GlobbingFilter`` and ``Grouper``.

Neither had any test coverage. As a result #76 (the filter mutating the
caller's exclude list) and the exact wildcard semantics of the grouper went
unnoticed.
'''
from pycallgraph.globbing_filter import GlobbingFilter
from pycallgraph.grouper import Grouper


# --------------------------------------------------------------------------
# GlobbingFilter
# --------------------------------------------------------------------------

def test_no_arguments_includes_everything():
    fltr = GlobbingFilter()
    assert fltr('anything.at.all') is True


def test_exclude_only():
    fltr = GlobbingFilter(exclude=['pycallgraph.*'])
    assert fltr('pycallgraph.tracer') is False
    assert fltr('my_module.main') is True


def test_include_only_rejects_anything_not_matching():
    fltr = GlobbingFilter(include=['calls.*'])
    assert fltr('calls.nop') is True
    assert fltr('other.thing') is False


def test_exclude_takes_priority_over_include():
    fltr = GlobbingFilter(include=['*'], exclude=['secret.*'])
    assert fltr('secret.thing') is False
    assert fltr('public.thing') is True


def test_unmatched_object_is_excluded():
    '''Passing through without matching either list means exclusion.'''
    fltr = GlobbingFilter(include=['a'], exclude=['b'])
    assert fltr('c') is False


def test_wildcards_use_fnmatch_semantics():
    fltr = GlobbingFilter(include=['pkg.sub.*'])
    assert fltr('pkg.sub.one') is True
    # fnmatch's '*' crosses '.' -- document the actual behaviour.
    assert fltr('pkg.sub.deep.one') is True


# --------------------------------------------------------------------------
# Grouper
# --------------------------------------------------------------------------

def test_group_by_top_level_module_by_default():
    grouper = Grouper()
    assert grouper('pkg.module.func') == 'pkg'


def test_group_with_no_dot_is_returned_whole():
    grouper = Grouper()
    assert grouper('toplevel') == 'toplevel'


def test_trailing_wildcard_group_collapses_to_its_prefix():
    '''
    A wildcard at the end of a group pattern is treated as noise: the group
    name is the pattern with the trailing '.*' removed, which for a
    dotted prefix means the *parent* is reported.
    '''
    grouper = Grouper(groups=['pkg.sub.*'])
    assert grouper('pkg.sub') == 'pkg'
    assert grouper('pkg.sub') == 'pkg'


def test_matching_group_without_trailing_wildcard_is_kept_verbatim():
    grouper = Grouper(groups=['pkg.special'])
    assert grouper('pkg.special') == 'pkg.special'


def test_interior_wildcard_is_kept():
    grouper = Grouper(groups=['pkg.*.inner'])
    assert grouper('pkg.mid.inner') == 'pkg.*.inner'


def test_first_matching_group_wins():
    '''
    Groups are tested in order. 'pkg.*' matches first and its trailing '.*'
    is stripped, so the reported group is 'pkg'.
    '''
    grouper = Grouper(groups=['pkg.*', 'pkg.special'])
    assert grouper('pkg.special') == 'pkg'
