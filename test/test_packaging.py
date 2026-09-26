'''
Acceptance tests for packaging and installation.

Background
----------
Issue #29: ``pip install python-call-graph`` failed with::

    File "setup.py", line 10, in <module>
      import pycallgraph
    ModuleNotFoundError: No module named 'pycallgraph'

``setup.py`` imported the package it was packaging in order to read the
version. That only works when the project directory happens to be on
``sys.path`` (CPython's legacy script-directory behaviour) and fails in any
build frontend that removes it. ``python -P setup.py`` reproduces it exactly.

The package metadata must therefore be readable *without importing the
package*.
'''
import ast
import importlib.util
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETUP_PY = os.path.join(REPO_ROOT, 'setup.py')
METADATA_PY = os.path.join(REPO_ROOT, 'pycallgraph', 'metadata.py')


def _clean_env(**extra):
    '''Environment without PYTHONPATH/PYTHONHOME, plus any extras.'''
    env = {
        k: v for k, v in os.environ.items()
        if k not in ('PYTHONPATH', 'PYTHONHOME')
    }
    env.update(extra)
    return env


def _read_metadata():
    '''Read ``pycallgraph/metadata.py`` by path, as ``setup.py`` does.'''
    namespace = {}
    exec(open(METADATA_PY, encoding='utf-8').read(), namespace)
    return namespace


def _setup_tree():
    with open(SETUP_PY) as handle:
        return ast.parse(handle.read(), filename=SETUP_PY)


def test_setup_does_not_import_the_package():
    '''
    ``setup.py`` must not import ``pycallgraph`` (or any submodule) at build
    time, because the source directory is not guaranteed to be importable.
    '''
    offenders = []
    for node in ast.walk(_setup_tree()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'pycallgraph':
                    offenders.append(alias.name)
                elif alias.name.startswith('pycallgraph.'):
                    offenders.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if module == 'pycallgraph' or module.startswith('pycallgraph.'):
                offenders.append(module)

    assert offenders == [], (
        'setup.py imports the package it is packaging: %r' % (offenders,)
    )


def test_setup_does_not_import_deprecated_test_command():
    '''
    ``setuptools.command.test`` is removed in current setuptools. Importing it
    makes packaging fail outright on modern build tooling.
    '''
    source = open(SETUP_PY).read()
    assert 'setuptools.command.test' not in source


def test_egg_info_succeeds_without_script_dir_on_path(tmp_path):
    '''
    Reproduces issue #29 directly.

    ``python -I`` (isolated mode) stops CPython from prepending the script's
    directory to ``sys.path``, which is exactly what pip and other modern build
    frontends do. ``-I`` exists on every supported interpreter, unlike ``-P``
    (added in 3.11), so the reproduction also runs on Python 3.8-3.10.
    '''
    result = subprocess.run(
        [
            sys.executable, '-I', SETUP_PY, 'egg_info',
            '--egg-base', str(tmp_path),
        ],
        cwd=REPO_ROOT,
        env=_clean_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert result.returncode == 0, result.stdout


def test_egg_info_reports_the_metadata_version(tmp_path):
    '''
    The version in the generated metadata comes from ``metadata.py``, proving
    the file-path reading path works end to end.
    '''
    result = subprocess.run(
        [
            sys.executable, '-I', SETUP_PY, 'egg_info',
            '--egg-base', str(tmp_path),
        ],
        cwd=REPO_ROOT,
        env=_clean_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert result.returncode == 0, result.stdout

    pkginfo = list(tmp_path.glob('*.egg-info/PKG-INFO'))
    assert pkginfo, 'no PKG-INFO was generated'

    contents = pkginfo[0].read_text(encoding='utf-8')
    version = _read_metadata()['__version__']
    assert 'Version: %s' % version in contents


def test_metadata_is_importable_without_initialising_package():
    '''
    ``pycallgraph.metadata`` is the single source of truth for version and
    author details and must have no heavy dependencies, so ``setup.py`` can
    read it by file path.
    '''
    spec = importlib.util.spec_from_file_location(
        '_pcg_metadata_probe', METADATA_PY
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.__version__
    assert module.__author__


def test_setup_reads_metadata_by_path_not_by_import():
    '''
    ``setup.py`` must not import the package (the build environment is
    isolated), so it reads ``metadata.py`` from disk. Parse the file and
    assert there is no real ``import pycallgraph`` statement.
    '''
    import ast

    tree = ast.parse(open(SETUP_PY).read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert not any(
        name == 'pycallgraph' or name.startswith('pycallgraph.')
        for name in imported
    )
    assert 'metadata.py' in open(SETUP_PY).read()


def test_license_is_a_valid_spdx_expression():
    '''
    PEP 639 requires the ``license`` field to be a valid SPDX expression. A
    free-text value like ``GPLv2`` is not, and modern setuptools treats the
    field as an expression.
    '''
    license_id = _read_metadata()['__license__']
    try:
        from packaging.licenses import canonicalize_license_expression
    except ImportError:
        canonicalize_license_expression = None

    if canonicalize_license_expression is not None:
        # Raises InvalidLicenseExpression when the value is not valid SPDX.
        canonicalize_license_expression(license_id)
    assert license_id.startswith('GPL-2.0')


def test_basic_import_does_not_require_graphviz():
    '''
    ``import pycallgraph`` (and the top-level outputs) must not need the
    ``dot`` binary; graphviz availability is checked in ``sanity_check`` only.
    '''
    result = subprocess.run(
        [sys.executable, '-c', 'import pycallgraph'],
        cwd=os.path.join(REPO_ROOT, 'test'),
        env=_clean_env(PYTHONPATH=REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize('name', ['pycallgraph', 'pycallgraph.output'])
def test_declared_packages_exist(name):
    path = os.path.join(REPO_ROOT, *name.split('.'))
    assert os.path.isdir(path)
    assert os.path.isfile(os.path.join(path, '__init__.py'))


def test_all_runtime_modules_are_covered_by_declared_packages():
    '''
    Guards against shipping an sdist/wheel that is missing a submodule.

    Every ``pycallgraph`` directory with an ``__init__.py`` should be present
    in a simple recursive package walk, which is what the build now uses.
    '''
    package_root = os.path.join(REPO_ROOT, 'pycallgraph')
    discovered = []
    for dirpath, _dirnames, filenames in os.walk(package_root):
        if '__init__.py' in filenames:
            rel = os.path.relpath(dirpath, REPO_ROOT)
            discovered.append(rel.replace(os.sep, '.'))

    assert 'pycallgraph' in discovered
    assert 'pycallgraph.output' in discovered


def test_sdist_contains_the_package(tmp_path):
    '''
    End-to-end guard for issue #29: a freshly built sdist must actually
    contain the ``pycallgraph`` package (and its metadata), so that installing
    it can never fall back to the failure the reporter saw.
    '''
    import tarfile

    result = subprocess.run(
        [sys.executable, SETUP_PY, 'sdist', '--dist-dir', str(tmp_path)],
        cwd=REPO_ROOT,
        env=_clean_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert result.returncode == 0, result.stdout

    archives = sorted(tmp_path.glob('python_call_graph-*.tar.gz'))
    assert archives, 'no sdist was produced'

    with tarfile.open(archives[-1]) as archive:
        names = archive.getnames()

    assert any(n.endswith('pycallgraph/__init__.py') for n in names)
    assert any(n.endswith('pycallgraph/metadata.py') for n in names)
    assert any(n.endswith('scripts/pycallgraph') for n in names)
