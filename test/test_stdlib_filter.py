'''
Acceptance tests for standard library detection.

Background
----------
``pycallgraph`` excludes standard library frames from a trace by default
(``include_stdlib=False``). It decides whether a module is part of the
standard library by comparing ``module.__file__`` against the interpreter's
library directories.

Those directories are reported by :mod:`sysconfig` using the *logical* install
location, which is frequently a symlink (Homebrew, asdf, conda and some
distro-packaged interpreters all do this). The path reported by
``module.__file__`` is the *real* path. Comparing the two without resolving
symlinks makes every standard library module look like user code, so stdlib
frames leak into the graph even though they were meant to be filtered out.
'''
import os
import sysconfig

import pytest

from pycallgraph.config import Config
from pycallgraph.tracer import TraceProcessor


@pytest.fixture
def trace_processor():
    return TraceProcessor([], Config(include_stdlib=False))


def test_stdlib_module_is_detected(trace_processor):
    '''A file inside the interpreter's standard library is recognised.'''
    stdlib = sysconfig.get_path('stdlib')
    assert trace_processor.is_module_stdlib(os.path.join(stdlib, 'os.py'))


@pytest.mark.parametrize(
    'key', ['stdlib', 'platstdlib', 'purelib', 'platlib']
)
def test_module_directories_are_detected(trace_processor, key):
    '''
    Every module directory reported by sysconfig is treated as library code.

    ``purelib``/``platlib`` (site-packages) are intentionally included here to
    preserve the historical semantics of ``include_stdlib``, which has always
    covered installed packages as well as the standard library.
    '''
    path = sysconfig.get_path(key)
    if not path or not os.path.isdir(path):
        pytest.skip(f'sysconfig path {key!r} is not a directory')

    assert trace_processor.is_module_stdlib(os.path.join(path, 'module.py'))


def test_symlinked_stdlib_module_is_detected(trace_processor, tmp_path):
    '''
    Regression: a module reached through a symlinked interpreter directory is
    still recognised as library code.

    This mirrors the real-world Homebrew/asdf/conda layout where the logical
    library path is a symlink to the real directory.
    '''
    real_stdlib = os.path.realpath(sysconfig.get_path('stdlib'))
    link = tmp_path / 'linked-stdlib'
    link.symlink_to(real_stdlib, target_is_directory=True)

    assert trace_processor.is_module_stdlib(str(link / 'os.py'))


def test_stdlib_detection_is_case_insensitive(trace_processor):
    '''
    Detection is case-insensitive, preserving long-standing behaviour.
    '''
    stdlib = sysconfig.get_path('stdlib')
    upper = os.path.join(stdlib, 'OS.PY').upper()
    assert trace_processor.is_module_stdlib(upper)


def test_non_library_module_is_not_detected(trace_processor, tmp_path):
    '''User code outside the interpreter directories is not library code.'''
    user_module = tmp_path / 'my_project' / 'module.py'
    user_module.parent.mkdir(parents=True)
    user_module.write_text('')

    assert not trace_processor.is_module_stdlib(str(user_module))
