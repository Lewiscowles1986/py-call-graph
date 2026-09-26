'''
The development requirements must not include dependencies the suite does not
need.

``torch`` was listed (with a Python-version conditional for 3.8) solely because
one test imported it to obtain a module without ``__file__``. That test no
longer needs it, so requiring contributors to install a multi-hundred-megabyte
package to run the tests is pure friction.
'''
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEVELOPMENT = os.path.join(REPO_ROOT, 'requirements', 'development.txt')


def _requirements():
    with open(DEVELOPMENT) as handle:
        lines = handle.read().splitlines()
    return [
        line.strip() for line in lines
        if line.strip() and not line.strip().startswith('#')
    ]


def test_development_requirements_exist():
    assert _requirements()


def test_torch_is_not_a_development_requirement():
    '''
    Nothing in the suite imports torch any more (see test_optional_deps.py),
    so it should not be a hard requirement for contributors.
    '''
    offenders = [
        requirement for requirement in _requirements()
        if re.match(r'^torch\b', requirement)
    ]
    assert offenders == [], (
        'torch is no longer needed to run the suite: %r' % (offenders,)
    )


def test_pytest_and_flake8_are_still_required():
    '''The tools CI actually runs must remain declared.'''
    joined = '\n'.join(_requirements())
    for tool in ('pytest', 'flake8'):
        assert tool in joined, tool


def test_every_declared_requirement_is_import_or_tool_related():
    '''
    Guard against a stray entry: each line should look like a package name,
    optionally pinned or marked.
    '''
    for requirement in _requirements():
        name = requirement
        for separator in ('==', '>=', '<=', '~=', '>', '<', '!=', ';'):
            name = name.split(separator)[0]
        name = name.strip()
        assert re.match(r'^[A-Za-z0-9_.\-\[\]]+$', name), requirement
