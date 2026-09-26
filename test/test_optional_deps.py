'''
The test suite must not require optional third-party packages.

``test_trace_processor`` used to import ``torch`` unguarded just to obtain a
frame whose module has no ``__file__``. That made the whole suite fail on any
machine without torch, which is most of them.
'''
import os
import re


def test_the_test_suite_does_not_import_torch():
    '''
    Importing the test modules must not pull in torch. This is checked by
    running the module finder over the source rather than trusting that no
    test happens to need it today.
    '''
    test_dir = os.path.dirname(os.path.abspath(__file__))
    offenders = []
    for name in sorted(os.listdir(test_dir)):
        if not name.endswith('.py'):
            continue
        path = os.path.join(test_dir, name)
        with open(path) as handle:
            source = handle.read()
        for optional in ('torch', 'numpy'):
            pattern = re.compile(
                r'^\s*import %s\b' % optional, re.MULTILINE)
            if pattern.search(source):
                offenders.append('%s imports %s' % (name, optional))

    assert offenders == [], (
        'optional dependencies must be guarded with importorskip: %r'
        % (offenders,)
    )
