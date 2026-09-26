'''
Acceptance tests for the package's public surface and project metadata.

These lock down the contract that other files (setup.py, docs, the command
line) depend on, so maintainer-facing refactors cannot silently break it.
'''
import os
import subprocess
import sys

import pycallgraph
from pycallgraph.config import Config


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(arguments):
    env = dict(os.environ)
    env['PYTHONPATH'] = REPO_ROOT
    return subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, 'scripts', 'pycallgraph'),
         arguments],
        cwd=REPO_ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def test_metadata_defines_the_fields_setup_reads():
    '''
    setup.py reads these by name from pycallgraph/metadata.py. If one is
    renamed, packaging breaks, so guard the names here.
    '''
    from pycallgraph import metadata

    for field in (
        '__version__', '__description__', '__author__', '__email__',
        '__license__', '__url__',
    ):
        assert getattr(metadata, field), 'missing %s' % field


def test_public_api_is_importable_from_the_package_root():
    '''The documented top-level imports stay available.'''
    for name in (
        'PyCallGraph', 'PyCallGraphException', 'Config', 'GlobbingFilter',
        'Grouper', 'Util', 'Color', 'ColorException', 'decorators',
    ):
        assert hasattr(pycallgraph, name), 'missing public name %s' % name


def test_stdlib_option_documents_its_full_scope():
    '''
    ``--stdlib`` controls standard library *and* installed (site-packages)
    modules. The help text should say so, so users are not surprised that
    site-packages is hidden by default.
    '''
    result = run_cli('--help')
    assert result.returncode == 0, result.stdout
    assert 'stdlib' in result.stdout.lower()
    assert 'site-packages' in result.stdout


def test_include_stdlib_defaults_to_off():
    assert Config().include_stdlib is False


def test_include_stdlib_can_be_enabled():
    assert Config(include_stdlib=True).include_stdlib is True
