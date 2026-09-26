'''
The test directory must not contain modules nothing imports.

``test/helpers.py`` (unused sleep wrappers) and ``test/fix_path.py`` (a path
bootstrap superseded by running pytest with the repository on PYTHONPATH) were
dead weight: neither was imported by any test, and ``fix_path.py`` was not even
collectable as a test.
'''
import os
import re

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def _imported_modules():
    modules = set()
    for name in os.listdir(TEST_DIR):
        if not name.endswith('.py'):
            continue
        with open(os.path.join(TEST_DIR, name)) as handle:
            source = handle.read()
        for match in re.finditer(
                r'^\s*(?:from|import)\s+([A-Za-z_][\w.]*)', source,
                re.MULTILINE):
            modules.add(match.group(1).split('.')[0])
        for match in re.finditer(
                r'^\s*from\s+\.([A-Za-z_][\w]*)', source, re.MULTILINE):
            modules.add(match.group(1))
    return modules


def test_no_orphan_test_modules():
    '''
    Every module in test/ must be either a test module (matching the test_*
    convention) or imported by something.
    '''
    imported = _imported_modules()
    orphans = []
    for name in sorted(os.listdir(TEST_DIR)):
        if not name.endswith('.py') or name == '__init__.py':
            continue
        module = name[:-3]
        if module in ('conftest', 'calls'):
            continue
        if module.startswith('test_'):
            continue
        if module not in imported:
            orphans.append(name)

    assert orphans == [], (
        'these test helpers are not imported by anything: %r' % (orphans,)
    )


def test_the_helpers_that_were_removed_are_gone():
    for name in ('helpers.py', 'fix_path.py'):
        assert not os.path.exists(os.path.join(TEST_DIR, name)), name
