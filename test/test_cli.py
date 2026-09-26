'''
Acceptance tests for the command line interface.

Two long-standing rough edges:

* Running with no arguments raised a raw ``AttributeError`` from inside
  ``Config.strip_argv`` instead of printing usage.
* Pointing at a script that does not exist raised a bare ``FileNotFoundError``
  traceback with no context, and the process exit code was not meaningful.
'''
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, 'scripts', 'pycallgraph')


def _run(*args, cwd=None):
    env = dict(os.environ)
    env['PYTHONPATH'] = REPO_ROOT
    return subprocess.run(
        [sys.executable, SCRIPT] + list(args),
        cwd=cwd or REPO_ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def _run_module(*args, cwd=None):
    env = dict(os.environ)
    env['PYTHONPATH'] = REPO_ROOT
    return subprocess.run(
        [sys.executable, '-m', 'pycallgraph'] + list(args),
        cwd=cwd or REPO_ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def test_no_arguments_prints_usage_and_exits_nonzero():
    result = _run()

    assert result.returncode != 0
    assert 'usage' in result.stdout.lower()
    assert 'Traceback' not in result.stdout
    assert 'AttributeError' not in result.stdout


def test_no_arguments_suggests_help():
    result = _run()
    assert '--help' in result.stdout or '-h' in result.stdout


def test_missing_script_reports_a_readable_error(tmp_path):
    missing = str(tmp_path / 'does_not_exist.py')
    result = _run('graphviz', '--', missing)

    assert result.returncode != 0
    assert 'Traceback' not in result.stdout
    assert 'does_not_exist.py' in result.stdout


def test_missing_script_error_mentions_the_problem(tmp_path):
    missing = str(tmp_path / 'nope.py')
    result = _run('graphviz', '--', missing)

    lowered = result.stdout.lower()
    assert 'could not find' in lowered or 'not found' in lowered


def test_help_still_works():
    result = _run('--help')

    assert result.returncode == 0
    assert 'Python Call Graph' in result.stdout


def test_running_a_script_writes_output(tmp_path):
    script = tmp_path / 'simple.py'
    script.write_text(
        'def nop():\n'
        '    pass\n'
        '\n'
        'def one_nop():\n'
        '    nop()\n'
        '\n'
        'one_nop()\n'
    )
    output = tmp_path / 'graph.dot'

    result = _run('graphviz', '--output-format', 'dot',
                  '-o', str(output), '--', str(script))

    assert result.returncode == 0, result.stdout
    assert output.exists()
    assert 'digraph G' in output.read_text()


def test_missing_script_exit_code_is_distinct_from_success(tmp_path):
    missing = str(tmp_path / 'absent.py')
    result = _run('graphviz', '--', missing)
    assert result.returncode != 0


# --------------------------------------------------------------------------
# python -m pycallgraph
# --------------------------------------------------------------------------

def test_module_entry_point_prints_help():
    '''``python -m pycallgraph`` must work like the console script.'''
    result = _run_module('--help')
    assert result.returncode == 0
    assert 'Python Call Graph' in result.stdout


def test_module_entry_point_traces_a_script(tmp_path):
    script = tmp_path / 'simple.py'
    script.write_text(
        'def nop():\n'
        '    pass\n'
        '\n'
        'def one_nop():\n'
        '    nop()\n'
        '\n'
        'one_nop()\n'
    )
    output = tmp_path / 'module.dot'

    result = _run_module('graphviz', '--output-format', 'dot',
                         '-o', str(output), '--', str(script))

    assert result.returncode == 0, result.stdout
    assert output.exists()
    assert 'digraph G' in output.read_text()


def test_module_entry_point_reports_a_missing_script(tmp_path):
    missing = str(tmp_path / 'absent.py')
    result = _run_module('graphviz', '--', missing)

    assert result.returncode != 0
    assert 'Traceback' not in result.stdout
    assert 'absent.py' in result.stdout


def test_the_script_wrapper_and_the_module_entry_point_agree(tmp_path):
    '''Both entry points must share one implementation.'''
    script = tmp_path / 'simple.py'
    script.write_text('def nop():\n    pass\nnop()\n')

    from_script = _run('graphviz', '--output-format', 'dot',
                       '-o', str(tmp_path / 'a.dot'), '--', str(script))
    from_module = _run_module('graphviz', '--output-format', 'dot',
                              '-o', str(tmp_path / 'b.dot'), '--', str(script))

    assert from_script.returncode == from_module.returncode == 0
    assert from_script.stdout == from_module.stdout


def test_console_script_entry_point_is_declared():
    '''
    Installing the package must provide a 'pycallgraph' console script whose
    target actually exists -- the reported regression was an entry point
    pointing at a missing module.
    '''
    from pycallgraph.cli import run
    assert callable(run)

    setup_py = os.path.join(REPO_ROOT, 'setup.py')
    with open(setup_py) as handle:
        source = handle.read()
    assert 'pycallgraph = pycallgraph.cli:run' in source
