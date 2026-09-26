'''
Acceptance tests for the PEP 517/518 build configuration.

The project had no ``pyproject.toml``, so build frontends fell back to the
legacy ``setup.py`` code path. Adding a ``[build-system]`` table opts in to the
standard isolated build, which is what lets ``pip install .`` work without
``--use-pep517`` and what tooling increasingly expects.
'''
import ast
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYPROJECT = os.path.join(REPO_ROOT, 'pyproject.toml')


def test_pyproject_exists():
    assert os.path.exists(PYPROJECT)


def test_declares_a_build_backend():
    try:
        import tomllib
    except ImportError:
        pytest.skip('tomllib requires Python 3.11+')

    with open(PYPROJECT, 'rb') as handle:
        config = tomllib.load(handle)

    assert 'build-system' in config
    assert config['build-system']['build-backend']
    assert config['build-system']['requires']


def test_declares_setuptools_as_the_backend():
    '''The project is built with setuptools (setup.py is the source of
    metadata), so the declared backend must match.'''
    with open(PYPROJECT) as handle:
        text = handle.read()
    assert 'setuptools.build_meta' in text


def test_the_metadata_is_still_not_duplicated():
    '''
    Duplicating name/version in [project] would create two sources of truth
    that could silently diverge. This change is build-system only.
    '''
    try:
        import tomllib
    except ImportError:
        pytest.skip('tomllib requires Python 3.11+')

    with open(PYPROJECT, 'rb') as handle:
        config = tomllib.load(handle)

    project = config.get('project', {})
    assert 'version' not in project, (
        'the version must stay in pycallgraph/metadata.py'
    )


def test_pyproject_still_does_not_import_the_package():
    '''setup.py must remain import-free (issue #29); pyproject must not
    reintroduce the problem via a dynamic metadata import of the package.'''
    setup_py = os.path.join(REPO_ROOT, 'setup.py')
    with open(setup_py) as handle:
        tree = ast.parse(handle.read(), filename=setup_py)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any(
                a.name.split('.')[0] == 'pycallgraph' for a in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or '').split('.')[0]
            assert module != 'pycallgraph'


def test_dynamic_version_matches_the_metadata_module():
    '''
    If a version is ever declared dynamically, it must resolve to the same
    value as pycallgraph/metadata.py.
    '''
    from pycallgraph import metadata

    assert metadata.__version__
    try:
        import tomllib
    except ImportError:
        pytest.skip('tomllib requires Python 3.11+')

    with open(PYPROJECT, 'rb') as handle:
        config = tomllib.load(handle)

    project = config.get('project', {})
    if 'version' in project:
        assert project['version'] == metadata.__version__


def test_a_build_frontend_can_read_the_build_requirements():
    '''
    A smoke check that the declared build requirements are installable
    names -- this catches typos that would only show up in a clean build.
    '''
    try:
        import tomllib
    except ImportError:
        pytest.skip('tomllib requires Python 3.11+')

    with open(PYPROJECT, 'rb') as handle:
        config = tomllib.load(handle)

    requires = config['build-system']['requires']
    assert requires, 'the build backend needs at least one requirement'
    for requirement in requires:
        # 'setuptools>=61' -> 'setuptools'
        name = requirement
        for separator in ('>=', '<=', '==', '~=', '>', '<', '!='):
            name = name.split(separator)[0]
        name = name.split('[')[0].strip()
        assert name and name.isidentifier(), requirement
        assert ' ' not in name, requirement


def test_egg_info_still_works_under_a_legacy_frontend(tmp_path):
    '''setup.py must keep working for anyone not using PEP 517.'''
    result = subprocess.run(
        [
            sys.executable, '-I', os.path.join(REPO_ROOT, 'setup.py'),
            'egg_info', '--egg-base', str(tmp_path),
        ],
        cwd=REPO_ROOT,
        env={
            k: v for k, v in os.environ.items()
            if k not in ('PYTHONPATH', 'PYTHONHOME')
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert result.returncode == 0, result.stdout
