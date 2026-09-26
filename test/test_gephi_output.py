'''
Tests for the Gephi GDF output.

Two defects:

* Field values were written unquoted (only the colour was quoted). GDF is a
  comma-separated format, so any function, module or group name containing a
  comma -- or a label containing a quote or newline -- produced a malformed
  file that Gephi cannot read.
* ``done()`` opened ``self.output_file`` directly, so ``-o ~/graph.gdf`` wrote
  a literal ``~`` directory instead of expanding it, unlike every other output,
  which calls ``normalize_path``.
'''
import os

import calls
from pycallgraph.config import Config
from pycallgraph.output.gephi import GephiOutput
from pycallgraph.pycallgraph import PyCallGraph


def _record(tmp_path, name='pycallgraph.gdf'):
    output = GephiOutput(output_file=str(tmp_path / name))
    with PyCallGraph(output=output, config=Config()):
        calls.one_nop()
    with open(output.output_file) as handle:
        return handle.read()


def test_nodes_and_edges_are_still_produced(tmp_path):
    generated = _record(tmp_path)

    assert 'nodedef> name VARCHAR' in generated
    assert 'edgedef> node1 VARCHAR, node2 VARCHAR' in generated
    assert 'calls.one_nop,calls.one_nop,calls,1' in generated
    assert 'calls.one_nop,calls.nop,1' in generated


def test_a_comma_in_a_name_is_quoted(tmp_path):
    '''
    A name containing a comma must be quoted, or the row gets an extra column
    and Gephi rejects the file.
    '''
    output = GephiOutput(output_file=str(tmp_path / 'comma.gdf'))

    with PyCallGraph(output=output, config=Config()) as graph:
        calls.one_nop()
        # Simulate a function whose fully-qualified name contains a comma.
        graph.tracer.processor.func_count['weird,module.func'] = 1

    with open(output.output_file) as handle:
        generated = handle.read()

    for line in generated.splitlines():
        if 'weird' in line:
            assert '"weird,module.func"' in line, (
                'a field containing a comma must be quoted: %r' % line
            )
            break
    else:
        raise AssertionError('the comma-containing node was not written')


def test_a_double_quote_in_a_value_is_escaped():
    '''
    GDF follows CSV-ish quoting, so an embedded double quote must be doubled.
    '''
    output = GephiOutput()

    assert output.escape('plain') == 'plain'
    assert output.escape('needs,quoting') == '"needs,quoting"'
    assert output.escape('has "quotes"') == '"has ""quotes"""'
    assert output.escape('both, "mixed"') == '"both, ""mixed"""'


def test_escape_leaves_simple_values_unquoted():
    output = GephiOutput()

    for value in ('calls.one_nop', 'my_module', '1234', 'true'):
        assert output.escape(value) == value


def test_a_newline_in_a_value_is_escaped():
    output = GephiOutput()
    escaped = output.escape('first\nsecond')

    assert escaped.startswith('"')
    assert escaped.endswith('"')
    # The raw newline must not appear, or it would break the row.
    assert '\n' not in escaped[1:-1]


def test_done_expands_a_user_path(tmp_path, monkeypatch):
    '''
    ``done()`` must expand '~' like the other outputs do.
    '''
    monkeypatch.setenv('HOME', str(tmp_path))
    output = GephiOutput(output_file='~/gephi.gdf')

    with PyCallGraph(output=output, config=Config()):
        calls.one_nop()

    assert os.path.exists(str(tmp_path / 'gephi.gdf')), (
        'the output file was not written under the expanded home directory'
    )
    assert not os.path.exists('~')


def test_done_expands_environment_variables(tmp_path, monkeypatch):
    monkeypatch.setenv('PYCG_GEPHI_DIR', str(tmp_path))
    output = GephiOutput(output_file='$PYCG_GEPHI_DIR/gephi.gdf')

    with PyCallGraph(output=output, config=Config()):
        calls.one_nop()

    assert os.path.exists(str(tmp_path / 'gephi.gdf'))


def test_output_file_is_closed_after_done(tmp_path):
    '''The file handle must not be left open.'''
    output = GephiOutput(output_file=str(tmp_path / 'closed.gdf'))

    with PyCallGraph(output=output, config=Config()):
        calls.one_nop()

    # If the handle were still open, re-opening and reading is still fine on
    # most platforms, so assert directly that no handle is retained.
    assert not getattr(output, '_handle', None)
