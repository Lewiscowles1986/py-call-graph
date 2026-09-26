'''
Tests guarding the contributor experience of running the suite.

A full local run used to leave output files behind (``pycallgraph.dot``,
``pycallgraph.json``, ``basic.png`` ...) because outputs were written into the
repository working directory instead of a temporary one, and the ``temp``
fixture leaked a file descriptor from ``tempfile.mkstemp``.
'''
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Files the outputs produce when they are told to write to the CWD.
GENERATED_NAMES = (
    'pycallgraph.dot',
    'pycallgraph.png',
    'pycallgraph.gdf',
    'pycallgraph.json',
    'pycallgraph.pickle',
    'basic.png',
)


def test_suite_does_not_leave_generated_files_in_the_repo_root():
    leftovers = [
        name for name in GENERATED_NAMES
        if os.path.exists(os.path.join(REPO_ROOT, name))
    ]
    message = (
        'the test suite wrote output into the repository root: {0}. '
        'Outputs should target pytest tmp_path.'.format(', '.join(leftovers))
    )
    assert leftovers == [], message


def test_conftest_no_longer_uses_mkstemp():
    '''mkstemp() leaks its file descriptor; the fixture is gone.'''
    with open(os.path.join(REPO_ROOT, 'test', 'conftest.py')) as handle:
        source = handle.read()

    assert 'mkstemp' not in source
    assert 'tempfile' not in source


def test_output_tests_use_tmp_path():
    for name in ('test_json.py', 'test_pickle.py', 'test_gephi.py',
                 'test_graphviz.py'):
        path = os.path.join(REPO_ROOT, 'test', name)
        with open(path) as handle:
            source = handle.read()
        assert 'tmp_path' in source, name + ' should use pytest tmp_path'


def test_generated_output_names_are_gitignored():
    '''Belt and braces: a stray run should not show up in git status.'''
    with open(os.path.join(REPO_ROOT, '.gitignore')) as handle:
        ignored = handle.read()

    for name in ('pycallgraph.dot', 'pycallgraph.png', 'pycallgraph.json',
                 'pycallgraph.pickle'):
        assert name in ignored, name + ' should be listed in .gitignore'
